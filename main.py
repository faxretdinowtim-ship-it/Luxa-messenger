from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, select, or_, delete
import uvicorn

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== БАЗА ДАННЫХ ==========
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite+aiosqlite:///./luxa.db"
else:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# ========== МОДЕЛИ ==========
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), unique=True, nullable=False)
    username = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserStatus(Base):
    __tablename__ = "user_status"
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), unique=True, nullable=False)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    from_phone = Column(String(20), nullable=False)
    to_phone = Column(String(20), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    message_type = Column(String(20), default="text")

class GeneralMessage(Base):
    __tablename__ = "general_messages"
    id = Column(Integer, primary_key=True)
    from_phone = Column(String(20), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    message_type = Column(String(20), default="text")

class Friend(Base):
    __tablename__ = "friends"
    id = Column(Integer, primary_key=True)
    user_phone = Column(String(20), nullable=False)
    friend_phone = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# ========== PYDANTIC ==========
class PhoneRequest(BaseModel): phone: str
class UserRegister(BaseModel): phone: str; username: str
class MessageSend(BaseModel): from_phone: str; to_phone: str; text: str; message_type: str = "text"
class GeneralMessageSend(BaseModel): from_phone: str; text: str; message_type: str = "text"
class FriendAction(BaseModel): user_phone: str; friend_phone: str
class DeleteChat(BaseModel): user_phone: str; other_phone: str

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Сервер и БД готовы!")

# ========== HTML СТРАНИЦА (фронтенд) ==========
HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes, viewport-fit=cover">
    <title>LUXA — мессенджер</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: #050508;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .app {
            width: 100%;
            max-width: 480px;
            height: 95vh;
            background: rgba(12, 12, 20, 0.9);
            backdrop-filter: blur(32px);
            border-radius: 48px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 0 0 1px rgba(255,255,255,0.05);
        }
        .screen {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 24px 20px;
            overflow-y: auto;
        }
        .hidden { display: none !important; }
        .logo-block { text-align: center; margin-bottom: 32px; }
        .logo-icon {
            width: 64px; height: 64px;
            background: linear-gradient(145deg, #fff, #ddd);
            border-radius: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 12px;
            font-size: 32px;
        }
        .logo-text { font-size: 28px; font-weight: 700; color: white; }
        .logo-sub { font-size: 11px; color: rgba(255,255,255,0.45); }
        .input-group { margin-bottom: 16px; }
        .input-label { font-size: 12px; color: rgba(255,255,255,0.6); margin-bottom: 6px; padding-left: 12px; }
        input {
            width: 100%;
            padding: 14px 18px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 40px;
            color: white;
            font-size: 15px;
            outline: none;
        }
        button {
            background: #7C3AED;
            border: none;
            border-radius: 44px;
            padding: 14px;
            color: white;
            font-weight: 600;
            font-size: 16px;
            cursor: pointer;
            margin-top: 12px;
            width: 100%;
        }
        .btn-outline {
            background: transparent;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .success, .error {
            margin-top: 12px;
            padding: 10px;
            border-radius: 30px;
            text-align: center;
            font-size: 13px;
            display: none;
        }
        .success { background: #10b981; }
        .error { background: #ef4444; }
        .friend-card, .chat-card {
            background: rgba(255,255,255,0.04);
            border-radius: 28px;
            padding: 12px 16px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 14px;
            cursor: pointer;
            border: 0.5px solid rgba(255,255,255,0.05);
        }
        .avatar {
            width: 48px; height: 48px;
            background: linear-gradient(145deg, #4F46E5, #6D28D9);
            border-radius: 26px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        .info { flex: 1; }
        .name { font-weight: 600; font-size: 15px; color: white; }
        .status { font-size: 11px; opacity: 0.6; margin-top: 3px; }
        .message {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 24px;
            font-size: 14px;
            margin-bottom: 6px;
        }
        .my-message {
            background: #7C3AED;
            align-self: flex-end;
            border-bottom-right-radius: 6px;
        }
        .their-message {
            background: rgba(255,255,255,0.08);
            align-self: flex-start;
            border-bottom-left-radius: 6px;
        }
        .msg-time { font-size: 9px; opacity: 0.5; margin-top: 4px; text-align: right; }
        .search-row { display: flex; gap: 8px; margin-bottom: 16px; }
        .search-row input { flex: 1; margin: 0; }
        .search-row button { width: auto; padding: 0 16px; margin: 0; }
        .small-btn {
            background: rgba(255,255,255,0.08);
            padding: 8px 16px;
            border-radius: 30px;
            font-size: 13px;
            cursor: pointer;
            display: inline-block;
        }
        .back-btn {
            width: 40px; height: 40px;
            background: rgba(255,255,255,0.06);
            border-radius: 30px;
            font-size: 22px;
            cursor: pointer;
        }
        .messages-area {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
            padding: 8px 4px;
        }
        .input-line {
            display: flex;
            gap: 8px;
            background: rgba(255,255,255,0.04);
            border-radius: 50px;
            padding: 6px 6px 6px 18px;
            margin-top: 12px;
        }
        .input-line input {
            flex: 1;
            background: transparent;
            border: none;
            padding: 10px 0;
            margin: 0;
        }
        .input-line button {
            width: 44px;
            height: 44px;
            margin: 0;
            padding: 0;
            font-size: 20px;
        }
        .flex-between { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
    </style>
</head>
<body>
<div class="app" id="app">
    <!-- Экран входа -->
    <div id="loginScreen" class="screen">
        <div class="logo-block">
            <div class="logo-icon">💎</div>
            <div class="logo-text">LUXA</div>
            <div class="logo-sub">PREMIUM MESSENGER</div>
        </div>
        <div class="input-group">
            <div class="input-label">📱 ТЕЛЕФОН</div>
            <input type="tel" id="loginPhone" placeholder="+7 999 888 77 66">
        </div>
        <div class="input-group">
            <div class="input-label">🏷️ ИМЯ</div>
            <input type="text" id="loginName" placeholder="Ваше имя">
        </div>
        <button id="doLoginBtn">ВОЙТИ</button>
        <div class="input-group" style="margin-top: 16px;">
            <div class="input-label">✏️ ИЗМЕНИТЬ НИК</div>
            <input type="text" id="newNick" placeholder="Новый ник">
        </div>
        <button id="updateProfileBtn" class="btn-outline">ОБНОВИТЬ ПРОФИЛЬ</button>
        <div id="successMsg" class="success"></div>
        <div id="errorMsg" class="error"></div>
    </div>

    <!-- Основной экран -->
    <div id="mainScreen" class="screen hidden">
        <div class="flex-between">
            <div class="logo-text" style="font-size: 22px;">💬 ЧАТЫ</div>
            <div><span id="myName" style="font-weight:600;"></span></div>
        </div>
        <div class="search-row">
            <input type="text" id="globalSearch" placeholder="🔍 Поиск по ID или имени">
            <button id="searchUserBtn">НАЙТИ</button>
        </div>
        <div style="display: flex; gap: 12px; margin-bottom: 16px;">
            <div class="small-btn" id="tabFriendsBtn">👥 ДРУЗЬЯ</div>
            <div class="small-btn" id="tabGlobalBtn">🌍 ОБЩИЙ ЧАТ</div>
        </div>
        <div id="friendsListPanel"></div>
        <div id="globalChatPanel" class="hidden"></div>
    </div>

    <!-- Экран чата -->
    <div id="chatDialog" class="screen hidden">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
            <button class="back-btn" id="closeChatBtn">←</button>
            <div style="flex:1"><strong id="dialogName" style="color:white;"></strong><div id="dialogStatus" class="status"></div></div>
        </div>
        <div id="chatMessages" class="messages-area"></div>
        <div class="input-line">
            <input type="text" id="msgInput" placeholder="Сообщение...">
            <button id="sendMsgBtn">➤</button>
        </div>
    </div>
</div>

<script>
    // ========== API URL = ТОТ ЖЕ САМЫЙ САЙТ ==========
    const API = window.location.origin;
    
    let currentUser = null;
    let activeChat = null;
    let currentFriends = [];
    let pollingInterval = null;
    let currentTab = 'friends';

    const loginDiv = document.getElementById('loginScreen');
    const mainDiv = document.getElementById('mainScreen');
    const chatDiv = document.getElementById('chatDialog');
    const friendsPanel = document.getElementById('friendsListPanel');
    const globalPanel = document.getElementById('globalChatPanel');
    const chatMessagesDiv = document.getElementById('chatMessages');
    const dialogNameSpan = document.getElementById('dialogName');
    const dialogStatusSpan = document.getElementById('dialogStatus');

    function showSuccess(msg) {
        const el = document.getElementById('successMsg');
        el.textContent = msg;
        el.style.display = 'block';
        setTimeout(() => el.style.display = 'none', 3000);
    }
    function showError(msg) {
        const el = document.getElementById('errorMsg');
        el.textContent = msg;
        el.style.display = 'block';
        setTimeout(() => el.style.display = 'none', 3000);
    }

    async function registerOrUpdate(phone, username) {
        const res = await fetch(`${API}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone, username })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.status === 'ok') return data.username;
        throw new Error(data.message || 'Ошибка');
    }

    document.getElementById('doLoginBtn').onclick = async () => {
        const phone = document.getElementById('loginPhone').value.trim();
        const username = document.getElementById('loginName').value.trim();
        if (!phone || !username) { showError('Заполните поля'); return; }
        try {
            const finalName = await registerOrUpdate(phone, username);
            currentUser = { phone, username: finalName };
            localStorage.setItem('luxa_user', JSON.stringify(currentUser));
            showSuccess(`Добро пожаловать, ${finalName}!`);
            setTimeout(() => startApp(), 500);
        } catch(e) { showError('Ошибка: ' + e.message); }
    };

    document.getElementById('updateProfileBtn').onclick = async () => {
        const newNick = document.getElementById('newNick').value.trim();
        if (!newNick) { showError('Введите новый ник'); return; }
        let phone = currentUser?.phone || document.getElementById('loginPhone').value.trim();
        if (!phone) { showError('Сначала войдите'); return; }
        try {
            const newName = await registerOrUpdate(phone, newNick);
            if (currentUser) currentUser.username = newName;
            localStorage.setItem('luxa_user', JSON.stringify(currentUser));
            showSuccess(`Ник изменён на "${newName}"`);
            document.getElementById('loginName').value = newName;
            document.getElementById('newNick').value = '';
            if (document.getElementById('myName')) document.getElementById('myName').innerText = newName;
        } catch(e) { showError('Ошибка: ' + e.message); }
    };

    async function updateOnline() {
        if (!currentUser) return;
        try {
            await fetch(`${API}/update_status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone: currentUser.phone })
            });
        } catch(e) {}
    }
    setInterval(updateOnline, 20000);

    async function getUserStatus(phone, isFriend) {
        try {
            const url = isFriend ? `${API}/get_status/${phone}?viewer_phone=${currentUser.phone}` : `${API}/get_status/${phone}`;
            const res = await fetch(url);
            const data = await res.json();
            if (data.is_online) return { text: 'онлайн', online: true };
            if (isFriend && data.last_seen_text) return { text: data.last_seen_text, online: false };
            return { text: 'не в сети', online: false };
        } catch { return { text: '…', online: false }; }
    }

    async function loadFriends() {
        const res = await fetch(`${API}/friends/${currentUser.phone}`);
        const data = await res.json();
        currentFriends = data;
        return currentFriends;
    }

    async function renderFriendsList() {
        const friends = await loadFriends();
        const usersRes = await fetch(`${API}/users`);
        const allUsers = await usersRes.json();
        let html = '';
        for (let f of friends) {
            const user = allUsers.find(u => u.phone === f.friend_phone);
            const name = user ? user.username : f.friend_phone;
            const status = await getUserStatus(f.friend_phone, true);
            html += `<div class="friend-card" data-phone="${f.friend_phone}">
                        <div class="avatar">👤</div>
                        <div class="info">
                            <div class="name">${escapeHtml(name)}</div>
                            <div class="status">${status.online ? '🟢 ' + status.text : '⚫ ' + status.text}</div>
                        </div>
                        <div>💬</div>
                    </div>`;
        }
        friendsPanel.innerHTML = html || '<div style="text-align:center; padding:40px;">➕ Добавьте друзей через поиск</div>';
        document.querySelectorAll('.friend-card').forEach(card => {
            card.onclick = () => openChat(card.dataset.phone);
        });
    }

    document.getElementById('searchUserBtn').onclick = async () => {
        const query = document.getElementById('globalSearch').value.trim();
        if (!query) return;
        const res = await fetch(`${API}/search_users?q=${encodeURIComponent(query)}`);
        const users = await res.json();
        const filtered = users.filter(u => u.phone !== currentUser.phone);
        let html = `<div style="margin:12px 0 8px;"><strong>🔍 РЕЗУЛЬТАТЫ</strong></div>`;
        for (let u of filtered) {
            const isFriend = currentFriends.some(f => f.friend_phone === u.phone);
            html += `<div class="friend-card" style="justify-content:space-between;">
                        <div style="display:flex; align-items:center; gap:14px;">
                            <div class="avatar">👤</div>
                            <div><strong>${escapeHtml(u.username)}</strong><br><small>${u.phone}</small></div>
                        </div>
                        ${!isFriend ? `<button class="small-btn" data-add="${u.phone}">➕ ДОБАВИТЬ</button>` : '<span style="opacity:0.5;">✓ друг</span>'}
                    </div>`;
        }
        const temp = document.createElement('div');
        temp.innerHTML = html;
        friendsPanel.prepend(temp);
        temp.querySelectorAll('[data-add]').forEach(btn => {
            btn.onclick = async (e) => {
                const friendPhone = btn.dataset.add;
                await fetch(`${API}/add_friend`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_phone: currentUser.phone, friend_phone: friendPhone })
                });
                await renderFriendsList();
                btn.remove();
            };
        });
    };

    async function loadGlobalMessages() {
        const res = await fetch(`${API}/general_messages`);
        const data = await res.json();
        const container = document.getElementById('globalMessages');
        if (!container) return;
        let html = '';
        for (let m of data.messages || []) {
            const isOut = m.from === currentUser.phone;
            html += `<div class="message ${isOut ? 'my-message' : 'their-message'}">${escapeHtml(m.text)}<div class="msg-time">${new Date(m.time).toLocaleTimeString()}</div></div>`;
        }
        container.innerHTML = html;
        container.scrollTop = container.scrollHeight;
    }

    async function sendGlobalMessage(text) {
        await fetch(`${API}/send_general`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ from_phone: currentUser.phone, text, message_type: 'text' })
        });
        loadGlobalMessages();
    }

    function showGlobalChat() {
        globalPanel.innerHTML = `<div id="globalMessages" style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:6px; padding:8px 4px; height:55vh;"></div>
            <div class="input-line"><input type="text" id="globalMsgInput" placeholder="Сообщение в общий чат..."><button id="globalSendBtn">➤</button></div>`;
        loadGlobalMessages();
        document.getElementById('globalSendBtn').onclick = () => {
            const inp = document.getElementById('globalMsgInput');
            if (inp.value.trim()) sendGlobalMessage(inp.value.trim());
            inp.value = '';
        };
        if (window.glbInterval) clearInterval(window.glbInterval);
        window.glbInterval = setInterval(loadGlobalMessages, 4000);
    }

    async function openChat(phone) {
        activeChat = phone;
        const usersRes = await fetch(`${API}/users`);
        const users = await usersRes.json();
        const partner = users.find(u => u.phone === phone);
        dialogNameSpan.innerText = partner ? partner.username : phone;
        const status = await getUserStatus(phone, true);
        dialogStatusSpan.innerText = status.text;
        mainDiv.classList.add('hidden');
        chatDiv.classList.remove('hidden');
        await loadPrivateMessages();
        if (pollingInterval) clearInterval(pollingInterval);
        pollingInterval = setInterval(loadPrivateMessages, 4000);
    }

    async function loadPrivateMessages() {
        if (!activeChat) return;
        const res = await fetch(`${API}/dialog/${currentUser.phone}/${activeChat}`);
        const data = await res.json();
        const wasBottom = chatMessagesDiv.scrollHeight - chatMessagesDiv.scrollTop - chatMessagesDiv.clientHeight < 50;
        chatMessagesDiv.innerHTML = '';
        for (let m of data.messages || []) {
            const isOut = m.from === currentUser.phone;
            const div = document.createElement('div');
            div.className = `message ${isOut ? 'my-message' : 'their-message'}`;
            div.innerHTML = `${escapeHtml(m.text)}<div class="msg-time">${new Date(m.time).toLocaleTimeString()}</div>`;
            chatMessagesDiv.appendChild(div);
        }
        if (wasBottom) chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
    }

    async function sendPrivateMessage(text) {
        if (!activeChat) return;
        await fetch(`${API}/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ from_phone: currentUser.phone, to_phone: activeChat, text, message_type: 'text' })
        });
        await loadPrivateMessages();
    }

    document.getElementById('sendMsgBtn').onclick = () => {
        const inp = document.getElementById('msgInput');
        if (inp.value.trim()) sendPrivateMessage(inp.value.trim());
        inp.value = '';
    };
    document.getElementById('closeChatBtn').onclick = () => {
        if (pollingInterval) clearInterval(pollingInterval);
        chatDiv.classList.add('hidden');
        mainDiv.classList.remove('hidden');
        activeChat = null;
        if (currentTab === 'friends') renderFriendsList();
        else switchTab('global');
    };

    function switchTab(tab) {
        currentTab = tab;
        if (tab === 'friends') {
            globalPanel.classList.add('hidden');
            friendsPanel.classList.remove('hidden');
            renderFriendsList();
            if (window.glbInterval) clearInterval(window.glbInterval);
        } else {
            friendsPanel.classList.add('hidden');
            globalPanel.classList.remove('hidden');
            showGlobalChat();
        }
    }
    document.getElementById('tabFriendsBtn').onclick = () => switchTab('friends');
    document.getElementById('tabGlobalBtn').onclick = () => switchTab('global');

    async function startApp() {
        document.getElementById('myName').innerText = currentUser.username;
        loginDiv.classList.add('hidden');
        mainDiv.classList.remove('hidden');
        await updateOnline();
        await renderFriendsList();
        switchTab('friends');
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[m]);
    }

    const saved = localStorage.getItem('luxa_user');
    if (saved) {
        try {
            currentUser = JSON.parse(saved);
            document.getElementById('loginPhone').value = currentUser.phone;
            document.getElementById('loginName').value = currentUser.username;
            startApp();
        } catch(e) {}
    }
</script>
</body>
</html>
"""

@app.get("/")
@app.get("/web")
async def serve_index():
    return HTMLResponse(content=HTML_PAGE)

# ========== API ЭНДПОИНТЫ ==========

@app.post("/register")
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()
    if user:
        return {"status": "ok", "username": user.username}
    new_user = User(phone=data.phone, username=data.username)
    db.add(new_user)
    await db.commit()
    return {"status": "ok", "username": data.username}

@app.post("/update_status")
async def update_status(req: PhoneRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserStatus).where(UserStatus.phone == req.phone))
    status = result.scalar_one_or_none()
    if status:
        status.is_online = True
        status.last_seen = datetime.utcnow()
    else:
        status = UserStatus(phone=req.phone, is_online=True, last_seen=datetime.utcnow())
        db.add(status)
    await db.commit()
    return {"status": "ok"}

@app.get("/get_status/{phone}")
async def get_status(phone: str, viewer_phone: str = None, db: AsyncSession = Depends(get_db)):
    is_friend = False
    if viewer_phone:
        result = await db.execute(select(Friend).where(Friend.user_phone == viewer_phone, Friend.friend_phone == phone))
        is_friend = result.scalar_one_or_none() is not None
    result = await db.execute(select(UserStatus).where(UserStatus.phone == phone))
    status = result.scalar_one_or_none()
    if not status:
        return {"is_online": False, "last_seen_text": "неизвестно"}
    if status.is_online:
        return {"is_online": True, "last_seen_text": "онлайн"}
    if is_friend:
        diff = datetime.utcnow() - status.last_seen
        if diff.days > 0:
            last_text = f"{diff.days} дн. назад"
        elif diff.seconds > 3600:
            last_text = f"{diff.seconds // 3600} ч. назад"
        elif diff.seconds > 60:
            last_text = f"{diff.seconds // 60} мин. назад"
        else:
            last_text = "только что"
        return {"is_online": False, "last_seen_text": last_text}
    return {"is_online": False, "last_seen_text": "недавно"}

@app.post("/add_friend")
async def add_friend(data: FriendAction, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Friend).where(Friend.user_phone == data.user_phone, Friend.friend_phone == data.friend_phone))
    if result.scalar_one_or_none():
        return {"status": "error"}
    db.add(Friend(user_phone=data.user_phone, friend_phone=data.friend_phone))
    await db.commit()
    return {"status": "ok"}

@app.get("/friends/{phone}")
async def get_friends(phone: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Friend).where(Friend.user_phone == phone))
    return [{"friend_phone": f.friend_phone} for f in result.scalars().all()]

@app.get("/search_users")
async def search_users(q: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(or_(User.username.ilike(f"%{q}%"), User.phone.ilike(f"%{q}%"))).limit(20))
    users = result.scalars().all()
    return [{"phone": u.phone, "username": u.username} for u in users]

@app.post("/send")
async def send_message(msg: MessageSend, db: AsyncSession = Depends(get_db)):
    new_msg = Message(from_phone=msg.from_phone, to_phone=msg.to_phone, text=msg.text, message_type=msg.message_type, timestamp=datetime.utcnow())
    db.add(new_msg)
    await db.commit()
    return {"status": "ok"}

@app.get("/dialog/{phone1}/{phone2}")
async def get_dialog(phone1: str, phone2: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).where(((Message.from_phone == phone1) & (Message.to_phone == phone2)) | ((Message.from_phone == phone2) & (Message.to_phone == phone1))).order_by(Message.timestamp))
    messages = result.scalars().all()
    return {"messages": [{"id": m.id, "from": m.from_phone, "text": m.text, "time": m.timestamp.isoformat(), "message_type": m.message_type} for m in messages]}

@app.post("/send_general")
async def send_general_message(msg: GeneralMessageSend, db: AsyncSession = Depends(get_db)):
    new_msg = GeneralMessage(from_phone=msg.from_phone, text=msg.text, message_type=msg.message_type, timestamp=datetime.utcnow())
    db.add(new_msg)
    await db.commit()
    return {"status": "ok"}

@app.get("/general_messages")
async def get_general_messages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GeneralMessage).order_by(GeneralMessage.timestamp))
    messages = result.scalars().all()
    users_result = await db.execute(select(User))
    users = {u.phone: u.username for u in users_result.scalars().all()}
    return {"messages": [{"id": m.id, "from": m.from_phone, "from_name": users.get(m.from_phone, m.from_phone), "text": m.text, "time": m.timestamp.isoformat(), "message_type": m.message_type} for m in messages]}

@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"phone": u.phone, "username": u.username} for u in users]

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
