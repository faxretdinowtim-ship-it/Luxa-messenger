from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
import sqlite3
from contextlib import contextmanager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== БАЗА ДАННЫХ ==========
DB_PATH = "luxa.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (phone TEXT PRIMARY KEY, username TEXT, created_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS user_status (phone TEXT PRIMARY KEY, is_online INTEGER, last_seen TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, from_phone TEXT, to_phone TEXT, text TEXT, timestamp TEXT, message_type TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS general_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, from_phone TEXT, text TEXT, timestamp TEXT, message_type TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS friends (user_phone TEXT, friend_phone TEXT, PRIMARY KEY (user_phone, friend_phone))")
    print("✅ База данных готова")

init_db()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# ========== МОДЕЛИ ==========
class UserRegister(BaseModel): phone: str; username: str
class MessageSend(BaseModel): from_phone: str; to_phone: str; text: str; message_type: str = "text"
class GeneralMessageSend(BaseModel): from_phone: str; text: str; message_type: str = "text"
class FriendAction(BaseModel): user_phone: str; friend_phone: str

# ========== API ==========
@app.post("/register")
async def register(data: UserRegister):
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE phone = ?", (data.phone,)).fetchone()
        if user:
            return {"status": "ok", "username": user["username"]}
        db.execute("INSERT INTO users (phone, username, created_at) VALUES (?, ?, ?)",
                   (data.phone, data.username, datetime.utcnow().isoformat()))
        db.commit()
        return {"status": "ok", "username": data.username}

@app.post("/update_status")
async def update_status(phone: str):
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO user_status (phone, is_online, last_seen) VALUES (?, ?, ?)",
                   (phone, 1, datetime.utcnow().isoformat()))
        db.commit()
    return {"status": "ok"}

@app.get("/get_status/{phone}")
async def get_status(phone: str, viewer_phone: str = None):
    with get_db() as db:
        status = db.execute("SELECT * FROM user_status WHERE phone = ?", (phone,)).fetchone()
        if not status:
            return {"is_online": False, "last_seen_text": "неизвестно"}
        if status["is_online"]:
            return {"is_online": True, "last_seen_text": "онлайн"}
        if viewer_phone:
            friend = db.execute("SELECT * FROM friends WHERE user_phone = ? AND friend_phone = ?",
                                (viewer_phone, phone)).fetchone()
            if friend:
                return {"is_online": False, "last_seen_text": "недавно"}
        return {"is_online": False, "last_seen_text": "не в сети"}

@app.post("/add_friend")
async def add_friend(data: FriendAction):
    with get_db() as db:
        db.execute("INSERT OR IGNORE INTO friends (user_phone, friend_phone) VALUES (?, ?)",
                   (data.user_phone, data.friend_phone))
        db.commit()
    return {"status": "ok"}

@app.get("/friends/{phone}")
async def get_friends(phone: str):
    with get_db() as db:
        friends = db.execute("SELECT friend_phone FROM friends WHERE user_phone = ?", (phone,)).fetchall()
        return [{"friend_phone": f["friend_phone"]} for f in friends]

@app.get("/search_users")
async def search_users(q: str):
    with get_db() as db:
        users = db.execute("SELECT phone, username FROM users WHERE phone LIKE ? OR username LIKE ? LIMIT 20",
                          (f"%{q}%", f"%{q}%")).fetchall()
        return [{"phone": u["phone"], "username": u["username"]} for u in users]

@app.post("/send")
async def send_message(msg: MessageSend):
    with get_db() as db:
        db.execute("INSERT INTO messages (from_phone, to_phone, text, timestamp, message_type) VALUES (?, ?, ?, ?, ?)",
                   (msg.from_phone, msg.to_phone, msg.text, datetime.utcnow().isoformat(), msg.message_type))
        db.commit()
    return {"status": "ok"}

@app.get("/dialog/{phone1}/{phone2}")
async def get_dialog(phone1: str, phone2: str):
    with get_db() as db:
        msgs = db.execute("""SELECT * FROM messages 
            WHERE (from_phone = ? AND to_phone = ?) OR (from_phone = ? AND to_phone = ?)
            ORDER BY timestamp""", (phone1, phone2, phone2, phone1)).fetchall()
        return {"messages": [{"id": m["id"], "from": m["from_phone"], "text": m["text"], 
                              "time": m["timestamp"], "message_type": m["message_type"]} for m in msgs]}

@app.post("/send_general")
async def send_general_message(msg: GeneralMessageSend):
    with get_db() as db:
        db.execute("INSERT INTO general_messages (from_phone, text, timestamp, message_type) VALUES (?, ?, ?, ?)",
                   (msg.from_phone, msg.text, datetime.utcnow().isoformat(), msg.message_type))
        db.commit()
    return {"status": "ok"}

@app.get("/general_messages")
async def get_general_messages():
    with get_db() as db:
        msgs = db.execute("SELECT * FROM general_messages ORDER BY timestamp").fetchall()
        users = db.execute("SELECT phone, username FROM users").fetchall()
        users_dict = {u["phone"]: u["username"] for u in users}
        return {"messages": [{"id": m["id"], "from": m["from_phone"], 
                              "from_name": users_dict.get(m["from_phone"], m["from_phone"]),
                              "text": m["text"], "time": m["timestamp"], 
                              "message_type": m["message_type"]} for m in msgs]}

@app.get("/users")
async def get_users():
    with get_db() as db:
        users = db.execute("SELECT phone, username FROM users").fetchall()
        return [{"phone": u["phone"], "username": u["username"]} for u in users]

# ========== HTML СТРАНИЦА (ТОТ САМЫЙ ТОПОВЫЙ ДИЗАЙН) ==========
HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes, viewport-fit=cover">
    <title>LUXA | DIAMOND PREMIUM</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        
        body {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Inter', system-ui, sans-serif;
            background: #020208;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
            position: relative;
        }
        
        /* ГИПЕР-РЕАЛИСТИЧНЫЙ 3D ФОН С АЛМАЗНЫМ СИЯНИЕМ */
        body::before {
            content: '';
            position: fixed;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: 
                radial-gradient(ellipse at 20% 25%, rgba(139, 92, 246, 0.3), transparent 70%),
                radial-gradient(ellipse at 85% 70%, rgba(99, 102, 241, 0.25), transparent 60%),
                radial-gradient(ellipse at 50% 50%, rgba(255,215,0,0.08), transparent 80%);
            z-index: -3;
            animation: cosmicDrift 30s ease infinite;
        }
        
        @keyframes cosmicDrift {
            0%, 100% { transform: translate(0,0) scale(1); }
            33% { transform: translate(0.8%, -0.5%) scale(1.01); }
            66% { transform: translate(-0.3%, 0.4%) scale(0.99); }
        }
        
        body::after {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(circle at 50% 50%, rgba(0,0,0,0) 0%, rgba(0,0,0,0.6) 100%);
            z-index: -2;
            pointer-events: none;
        }
        
        /* ПРЕМИУМ СТЕКЛЯННЫЙ КОНТЕЙНЕР */
        .app {
            width: 100%;
            max-width: 480px;
            height: 95vh;
            max-height: 820px;
            background: rgba(10, 10, 22, 0.55);
            backdrop-filter: blur(40px) saturate(200%);
            border-radius: 60px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 45px 75px -35px rgba(0,0,0,0.7), 0 0 0 1.5px rgba(255,215,0,0.2), inset 0 1px 0 rgba(255,255,255,0.08);
            animation: glassAscend 0.6s cubic-bezier(0.16,1,0.3,1);
        }
        
        @keyframes glassAscend {
            from { opacity: 0; transform: translateY(40px) scale(0.94); backdrop-filter: blur(0px); }
            to { opacity: 1; transform: translateY(0) scale(1); backdrop-filter: blur(40px) saturate(200%); }
        }
        
        .page {
            flex: 1;
            overflow-y: auto;
            padding: 24px 20px;
            display: none;
            animation: fadeSlide 0.4s cubic-bezier(0.2,0.9,0.4,1.1);
        }
        .page.active { display: block; }
        @keyframes fadeSlide {
            from { opacity: 0; transform: translateX(15px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        /* БРИЛЛИАНТОВОЕ МЕНЮ */
        .diamond-menu {
            background: rgba(8, 8, 18, 0.9);
            backdrop-filter: blur(30px);
            display: flex;
            justify-content: space-around;
            padding: 12px 16px 24px;
            border-top: 0.5px solid rgba(255,215,0,0.25);
        }
        .menu-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
            cursor: pointer;
            padding: 8px 20px;
            border-radius: 50px;
            transition: all 0.3s cubic-bezier(0.2,0.9,0.4,1.2);
        }
        .menu-item.active {
            background: rgba(255,215,0,0.12);
            transform: translateY(-3px);
            box-shadow: 0 0 15px rgba(255,215,0,0.2);
        }
        .menu-icon { font-size: 26px; filter: drop-shadow(0 0 5px rgba(255,215,0,0.3)); }
        .menu-label {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
            color: rgba(255,255,255,0.5);
        }
        .menu-item.active .menu-label {
            color: #FFD700;
            text-shadow: 0 0 6px rgba(255,215,0,0.6);
        }
        
        /* ЗОЛОТОЙ ХЕДЕР */
        .gold-header {
            padding: 18px 22px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 0.5px solid rgba(255,215,0,0.2);
            background: rgba(0,0,0,0.15);
        }
        .logo-diamond {
            font-size: 22px;
            font-weight: 800;
            background: linear-gradient(145deg, #FFD700, #FFA500, #FFD700);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            letter-spacing: -0.5px;
            text-shadow: 0 0 8px rgba(255,215,0,0.3);
        }
        .profile-diamond {
            background: rgba(255,215,0,0.1);
            padding: 6px 16px;
            border-radius: 40px;
            font-size: 13px;
            font-weight: 600;
            color: #FFD700;
            border: 0.5px solid rgba(255,215,0,0.3);
            backdrop-filter: blur(4px);
        }
        
        /* ЭЛИТНЫЕ КАРТОЧКИ */
        .elite-card {
            background: rgba(255,255,255,0.04);
            backdrop-filter: blur(12px);
            border-radius: 32px;
            padding: 14px 18px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 16px;
            cursor: pointer;
            border: 0.5px solid rgba(255,215,0,0.2);
            transition: all 0.25s ease;
            box-shadow: 0 6px 16px -8px rgba(0,0,0,0.3);
        }
        .elite-card:hover { transform: translateX(5px); border-color: rgba(255,215,0,0.5); background: rgba(255,255,255,0.06); }
        .elite-card:active { transform: scale(0.98); }
        
        .avatar-diamond {
            width: 56px; height: 56px;
            background: linear-gradient(145deg, #8B5CF6, #4F46E5);
            border-radius: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            box-shadow: 0 8px 18px -8px rgba(0,0,0,0.4);
        }
        .info-diamond { flex: 1; }
        .name-diamond { font-weight: 700; font-size: 17px; color: #FFF5E0; letter-spacing: -0.2px; }
        .status-diamond { font-size: 12px; opacity: 0.7; margin-top: 4px; color: rgba(255,255,255,0.7); }
        
        /* ЛЮКСОВЫЕ СООБЩЕНИЯ */
        .luxury-message {
            max-width: 80%;
            padding: 12px 20px;
            border-radius: 32px;
            font-size: 15px;
            margin-bottom: 10px;
            animation: messageReveal 0.35s cubic-bezier(0.2,0.9,0.4,1.2);
            position: relative;
            box-shadow: 0 6px 20px -10px rgba(0,0,0,0.3);
        }
        @keyframes messageReveal {
            from { opacity: 0; transform: translateY(14px) scale(0.96); filter: blur(2px); }
            to { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
        }
        .msg-out {
            background: linear-gradient(135deg, #8B5CF6, #6366F1);
            align-self: flex-end;
            border-bottom-right-radius: 10px;
            color: white;
            box-shadow: 0 0 18px rgba(139,92,246,0.4);
        }
        .msg-in {
            background: rgba(35, 35, 55, 0.85);
            backdrop-filter: blur(12px);
            align-self: flex-start;
            border-bottom-left-radius: 10px;
            color: #F0F0FF;
            border: 0.5px solid rgba(255,215,0,0.25);
        }
        .msg-footer {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 6px;
            font-size: 9px;
            opacity: 0.6;
        }
        .delivered-icon { color: #4ade80; }
        
        /* ПРЕМИУМ ПОЛЯ ВВОДА */
        .input-premium {
            display: flex;
            gap: 12px;
            background: rgba(255,255,255,0.05);
            border-radius: 60px;
            padding: 6px 6px 6px 24px;
            margin: 12px;
            border: 0.5px solid rgba(255,215,0,0.25);
            backdrop-filter: blur(15px);
        }
        .input-premium:focus-within {
            border-color: #FFD700;
            box-shadow: 0 0 20px rgba(255,215,0,0.15);
        }
        .input-premium input {
            flex: 1;
            background: transparent;
            border: none;
            padding: 14px 0;
            color: white;
            font-size: 15px;
            outline: none;
        }
        .input-premium button {
            width: 52px;
            height: 52px;
            background: linear-gradient(135deg, #8B5CF6, #6366F1);
            border-radius: 52px;
            padding: 0;
            font-size: 22px;
            margin: 0;
            box-shadow: 0 0 12px rgba(99,102,241,0.5);
            transition: all 0.2s;
        }
        .input-premium button:active { transform: scale(0.94); }
        
        input, button { width: 100%; }
        input {
            padding: 16px 20px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,215,0,0.2);
            border-radius: 50px;
            color: white;
            font-size: 15px;
            outline: none;
        }
        input:focus { border-color: #FFD700; box-shadow: 0 0 12px rgba(255,215,0,0.2); }
        button {
            background: linear-gradient(135deg, #8B5CF6, #6366F1);
            border: none;
            border-radius: 56px;
            padding: 16px;
            color: white;
            font-weight: 700;
            font-size: 16px;
            cursor: pointer;
            margin-top: 12px;
            transition: all 0.2s;
            box-shadow: 0 4px 15px rgba(99,102,241,0.3);
        }
        button:active { transform: scale(0.97); }
        
        .search-row { display: flex; gap: 12px; margin-bottom: 20px; }
        .small-btn-gold {
            background: rgba(255,215,0,0.12);
            padding: 8px 16px;
            border-radius: 40px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            color: #FFD700;
            border: 0.5px solid rgba(255,215,0,0.3);
        }
        .back-gold {
            background: rgba(255,215,0,0.1);
            padding: 8px 20px;
            border-radius: 50px;
            font-size: 14px;
            font-weight: 600;
            color: #FFD700;
            cursor: pointer;
            display: inline-block;
            margin-bottom: 16px;
        }
        .back-gold:active { transform: scale(0.96); }
        
        .success, .error {
            padding: 12px;
            border-radius: 60px;
            text-align: center;
            margin-top: 12px;
            display: none;
            font-weight: 500;
        }
        .success { background: #10b981; box-shadow: 0 0 15px #10b98140; }
        .error { background: #ef4444; }
        .flex-between { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .scroll-area { height: 55vh; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
        .hidden { display: none; }
        
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
        ::-webkit-scrollbar-thumb { background: #FFD700; border-radius: 10px; box-shadow: 0 0 5px #FFD700; }
    </style>
</head>
<body>
<div class="app" id="app">
    <!-- ЛОГИН -->
    <div id="loginPage" class="page active" style="display: flex; flex-direction: column; justify-content: center;">
        <div style="text-align: center; margin-bottom: 40px;">
            <div style="font-size: 80px; margin-bottom: 12px; text-shadow: 0 0 30px #FFD700;">💎</div>
            <div style="font-size: 36px; font-weight: 800; background: linear-gradient(145deg, #FFD700, #FFA500); -webkit-background-clip: text; background-clip: text; color: transparent;">LUXA</div>
            <div style="font-size: 11px; letter-spacing: 3px; color: rgba(255,215,0,0.6); margin-top: 6px;">DIAMOND PREMIUM</div>
        </div>
        <input type="tel" id="loginPhone" placeholder="ТЕЛЕФОН" style="margin-bottom: 12px;">
        <input type="text" id="loginName" placeholder="ИМЯ" style="margin-bottom: 20px;">
        <button id="doLoginBtn">ВОЙТИ</button>
        <input type="text" id="newNick" placeholder="НОВЫЙ НИК" style="margin-top: 20px;">
        <button id="updateProfileBtn" style="background: transparent; border: 1px solid rgba(255,215,0,0.4);">ОБНОВИТЬ</button>
        <div id="successMsg" class="success"></div>
        <div id="errorMsg" class="error"></div>
    </div>

    <div id="mainApp" style="display: none; flex-direction: column; flex: 1;">
        <div class="gold-header">
            <div class="logo-diamond">LUXA DIAMOND</div>
            <div class="profile-diamond" id="userNameDisplay"></div>
        </div>

        <div id="chatsPage" class="page active">
            <div class="flex-between"><div style="font-weight: 700; color: #FFD700; font-size: 18px;">💎 VIP ЧАТЫ</div></div>
            <div id="friendsList"></div>
        </div>

        <div id="contactsPage" class="page">
            <div class="search-row"><input type="text" id="searchInput" placeholder="🔍 ПОИСК ПО ID / ИМЕНИ"><button id="searchBtn" style="width: auto; padding: 0 24px;">ИСКАТЬ</button></div>
            <div id="searchResults"></div>
        </div>

        <div id="globalPage" class="page">
            <div style="font-weight: 700; color: #FFD700; font-size: 18px; margin-bottom: 16px;">🌍 ОБЩИЙ ЧАТ</div>
            <div id="globalMessages" class="scroll-area"></div>
            <div class="input-premium"><input type="text" id="globalMsgInput" placeholder="Сообщение в общий чат..."><button id="globalSendBtn">➤</button></div>
        </div>

        <div id="chatPage" class="page">
            <div class="back-gold" id="closeChatBtn">← НАЗАД</div>
            <div style="text-align: center; font-weight: 700; font-size: 18px; color: #FFD700; margin-bottom: 16px;" id="chatPartnerName"></div>
            <div id="chatMessagesArea" class="scroll-area" style="height: 55vh;"></div>
            <div class="input-premium"><input type="text" id="chatMsgInput" placeholder="Сообщение..."><button id="sendChatMsgBtn">➤</button></div>
        </div>

        <div class="diamond-menu">
            <div class="menu-item active" data-page="chats"><div class="menu-icon">💬</div><div class="menu-label">ЧАТЫ</div></div>
            <div class="menu-item" data-page="contacts"><div class="menu-icon">👥</div><div class="menu-label">КОНТАКТЫ</div></div>
            <div class="menu-item" data-page="global"><div class="menu-icon">🌍</div><div class="menu-label">ОБЩИЙ</div></div>
        </div>
    </div>
</div>

<script>
    const API = window.location.origin;
    let currentUser = null, activeChat = null, currentFriends = [], pollingChat = null, glbInt = null;

    async function regUser(phone, name) {
        const r = await fetch(`${API}/register`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ phone, username:name }) });
        const d = await r.json();
        if(d.status==='ok') return d.username;
        throw new Error('Ошибка');
    }

    document.getElementById('doLoginBtn').onclick = async () => {
        const phone = document.getElementById('loginPhone').value.trim();
        const name = document.getElementById('loginName').value.trim();
        if(!phone || !name) return showError('Заполните поля');
        try {
            const final = await regUser(phone, name);
            currentUser = { phone, username:final };
            localStorage.setItem('luxa_user', JSON.stringify(currentUser));
            showSuccess(`Добро пожаловать, ${final}!`);
            setTimeout(()=>initApp(), 500);
        } catch(e) { showError(e.message); }
    };

    document.getElementById('updateProfileBtn').onclick = async () => {
        const newN = document.getElementById('newNick').value.trim();
        if(!newN) return showError('Введите ник');
        let phone = currentUser?.phone || document.getElementById('loginPhone').value.trim();
        if(!phone) return showError('Сначала войдите');
        try {
            const newName = await regUser(phone, newN);
            if(currentUser) currentUser.username = newName;
            localStorage.setItem('luxa_user', JSON.stringify(currentUser));
            showSuccess(`Ник изменён на "${newName}"`);
            document.getElementById('loginName').value = newName;
            document.getElementById('newNick').value = '';
            document.getElementById('userNameDisplay').innerText = newName;
        } catch(e) { showError(e.message); }
    };

    function showSuccess(m){ let e=document.getElementById('successMsg'); e.innerText=m; e.style.display='block'; setTimeout(()=>e.style.display='none',2500); }
    function showError(m){ let e=document.getElementById('errorMsg'); e.innerText=m; e.style.display='block'; setTimeout(()=>e.style.display='none',2500); }

    async function updateOnline(){
        if(!currentUser) return;
        await fetch(`${API}/update_status?phone=${currentUser.phone}`,{ method:'POST' });
    }
    setInterval(updateOnline,25000);

    async function loadFriends(){
        const r=await fetch(`${API}/friends/${currentUser.phone}`); return await r.json();
    }

    async function renderChats(){
        const friends=await loadFriends();
        const usersR=await fetch(`${API}/users`); const allUsers=await usersR.json();
        let html='';
        for(let f of friends){
            const user=allUsers.find(u=>u.phone===f.friend_phone);
            const name=user?user.username:f.friend_phone;
            html+=`<div class="elite-card" data-phone="${f.friend_phone}"><div class="avatar-diamond">👤</div><div class="info-diamond"><div class="name-diamond">${escapeHtml(name)}</div><div class="status-diamond">💎 ЭЛИТА</div></div><div>💬</div></div>`;
        }
        document.getElementById('friendsList').innerHTML = html || '<div style="text-align:center; padding:40px;">➕ Добавьте друзей в "КОНТАКТЫ"</div>';
        document.querySelectorAll('.elite-card').forEach(c=>c.onclick=()=>openChat(c.dataset.phone));
    }

    document.getElementById('searchBtn').onclick = async ()=>{
        const q=document.getElementById('searchInput').value.trim();
        if(!q) return;
        const r=await fetch(`${API}/search_users?q=${encodeURIComponent(q)}`);
        const users=await r.json();
        const filtered=users.filter(u=>u.phone!==currentUser.phone);
        let html='';
        for(let u of filtered){
            const isFriend=currentFriends.some(f=>f.friend_phone===u.phone);
            html+=`<div class="elite-card" style="justify-content:space-between;"><div style="display:flex; gap:14px;"><div class="avatar-diamond">👤</div><div><strong>${escapeHtml(u.username)}</strong><br><small>${u.phone}</small></div></div>${!isFriend?`<button class="small-btn-gold" data-add="${u.phone}">➕ ДОБАВИТЬ</button>`:'<span style="color:#FFD700;">◆ ДРУГ</span>'}</div>`;
        }
        document.getElementById('searchResults').innerHTML = html || '<div style="text-align:center; padding:40px;">Не найдено</div>';
        document.querySelectorAll('[data-add]').forEach(btn=>btn.onclick=async e=>{
            const fPhone=btn.dataset.add;
            await fetch(`${API}/add_friend`,{ method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ user_phone:currentUser.phone, friend_phone:fPhone }) });
            await renderChats(); btn.remove();
        });
    };

    let lastGlobalCount=0;
    async function loadGlobal(){
        const r=await fetch(`${API}/general_messages`); const d=await r.json();
        const container=document.getElementById('globalMessages');
        if(!container) return;
        const msgs=d.messages||[];
        const wasBottom=container.scrollHeight-container.scrollTop-container.clientHeight<50;
        let html='';
        for(let m of msgs){
            const isOut=m.from===currentUser.phone;
            html+=`<div class="luxury-message ${isOut?'msg-out':'msg-in'}">${escapeHtml(m.text)}<div class="msg-footer"><span class="delivered-icon">✓ доставлено</span></div></div>`;
        }
        container.innerHTML=html;
        if(wasBottom) container.scrollTop=container.scrollHeight;
        lastGlobalCount=msgs.length;
    }
    async function sendGlobal(t){ await fetch(`${API}/send_general`,{ method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ from_phone:currentUser.phone, text:t, message_type:'text' }) }); loadGlobal(); }
    document.getElementById('globalSendBtn').onclick=()=>{ let inp=document.getElementById('globalMsgInput'); if(inp.value.trim()) sendGlobal(inp.value.trim()); inp.value=''; };

    async function openChat(phone){
        activeChat=phone;
        const usersR=await fetch(`${API}/users`); const users=await usersR.json();
        const partner=users.find(u=>u.phone===phone);
        document.getElementById('chatPartnerName').innerText=partner?partner.username:phone;
        switchPage('chat');
        await loadPrivate();
        if(pollingChat) clearInterval(pollingChat);
        pollingChat=setInterval(loadPrivate,4000);
    }

    let lastPrivateCount=0;
    async function loadPrivate(){
        if(!activeChat) return;
        const r=await fetch(`${API}/dialog/${currentUser.phone}/${activeChat}`); const d=await r.json();
        const container=document.getElementById('chatMessagesArea');
        if(!container) return;
        const msgs=d.messages||[];
        const wasBottom=container.scrollHeight-container.scrollTop-container.clientHeight<50;
        let html='';
        for(let m of msgs){
            const isOut=m.from===currentUser.phone;
            html+=`<div class="luxury-message ${isOut?'msg-out':'msg-in'}">${escapeHtml(m.text)}<div class="msg-footer"><span class="delivered-icon">✓ доставлено</span></div></div>`;
        }
        container.innerHTML=html;
        if(wasBottom) container.scrollTop=container.scrollHeight;
        lastPrivateCount=msgs.length;
    }

    async function sendPrivate(t){
        if(!activeChat) return;
        await fetch(`${API}/send`,{ method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ from_phone:currentUser.phone, to_phone:activeChat, text:t, message_type:'text' }) });
        loadPrivate();
    }

    document.getElementById('sendChatMsgBtn').onclick=()=>{ let inp=document.getElementById('chatMsgInput'); if(inp.value.trim()) sendPrivate(inp.value.trim()); inp.value=''; };
    document.getElementById('closeChatBtn').onclick=()=>{ if(pollingChat) clearInterval(pollingChat); activeChat=null; switchPage('chats'); renderChats(); };

    function switchPage(p){
        document.querySelectorAll('.page').forEach(v=>v.classList.remove('active'));
        document.getElementById(`${p}Page`).classList.add('active');
        document.querySelectorAll('.menu-item').forEach(v=>v.classList.remove('active'));
        document.querySelector(`.menu-item[data-page="${p}"]`).classList.add('active');
        if(p==='chats') renderChats();
        if(p==='global') loadGlobal();
    }
    document.querySelectorAll('.menu-item').forEach(v=>v.onclick=()=>switchPage(v.dataset.page));

    async function initApp(){
        document.getElementById('userNameDisplay').innerText=currentUser.username;
        document.getElementById('loginPage').style.display='none';
        document.getElementById('mainApp').style.display='flex';
        await renderChats();
        switchPage('chats');
        updateOnline();
        if(glbInt) clearInterval(glbInt);
        glbInt=setInterval(loadGlobal,5000);
    }

    function escapeHtml(s){ if(!s) return ''; return s.replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]); }

    const saved=localStorage.getItem('luxa_user');
    if(saved){
        try{ currentUser=JSON.parse(saved); document.getElementById('loginPhone').value=currentUser.phone; document.getElementById('loginName').value=currentUser.username; initApp(); }catch(e){}
    }
</script>
</body>
</html>"""

@app.get("/")
@app.get("/web")
async def serve_index():
    return HTMLResponse(content=HTML_PAGE)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
