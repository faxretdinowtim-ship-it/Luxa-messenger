from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, select, or_
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

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Сервер и БД готовы!")

# ========== HTML СТРАНИЦА (клиповый мессенджер) ==========
HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes, viewport-fit=cover">
    <title>LUXA — клиповый мессенджер</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: #050508;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }
        .app {
            width: 100%;
            max-width: 480px;
            height: 100vh;
            background: rgba(12, 12, 20, 0.95);
            backdrop-filter: blur(32px);
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
        }
        .page {
            flex: 1;
            overflow-y: auto;
            padding: 20px 16px;
            display: none;
            animation: pageSlide 0.3s ease;
        }
        .page.active {
            display: block;
        }
        @keyframes pageSlide {
            from { opacity: 0; transform: translateX(20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        .bottom-menu {
            background: rgba(20, 20, 30, 0.95);
            backdrop-filter: blur(20px);
            display: flex;
            justify-content: space-around;
            padding: 10px 16px 20px;
            border-top: 0.5px solid rgba(255,255,255,0.08);
        }
        .menu-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            transition: 0.2s;
            padding: 8px 12px;
            border-radius: 30px;
        }
        .menu-item.active {
            background: rgba(124, 58, 237, 0.2);
        }
        .menu-icon {
            font-size: 24px;
        }
        .menu-label {
            font-size: 11px;
            color: rgba(255,255,255,0.6);
        }
        .menu-item.active .menu-label {
            color: #7C3AED;
        }
        .header {
            padding: 16px 20px;
            border-bottom: 0.5px solid rgba(255,255,255,0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo {
            font-size: 20px;
            font-weight: 700;
            background: linear-gradient(135deg, #fff, #a78bfa);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        .profile-badge {
            background: rgba(255,255,255,0.1);
            padding: 6px 12px;
            border-radius: 30px;
            font-size: 12px;
        }
        input {
            width: 100%;
            padding: 14px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 30px;
            color: white;
            font-size: 15px;
            outline: none;
        }
        button {
            background: #7C3AED;
            border: none;
            border-radius: 40px;
            padding: 12px 20px;
            color: white;
            font-weight: 600;
            cursor: pointer;
        }
        .friend-card, .user-card {
            background: rgba(255,255,255,0.04);
            border-radius: 24px;
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
            font-size: 22px;
        }
        .info { flex: 1; }
        .name { font-weight: 600; font-size: 15px; color: white; }
        .sub { font-size: 11px; opacity: 0.5; margin-top: 3px; }
        .message-bubble {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 24px;
            font-size: 14px;
            margin-bottom: 8px;
        }
        .my-msg {
            background: #7C3AED;
            align-self: flex-end;
            border-bottom-right-radius: 6px;
        }
        .their-msg {
            background: rgba(255,255,255,0.08);
            align-self: flex-start;
            border-bottom-left-radius: 6px;
        }
        .chat-area {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
            padding: 12px;
        }
        .input-row {
            display: flex;
            gap: 8px;
            background: rgba(255,255,255,0.04);
            border-radius: 50px;
            padding: 6px 6px 6px 18px;
            margin: 12px;
        }
        .input-row input {
            flex: 1;
            background: transparent;
            border: none;
            padding: 10px 0;
        }
        .input-row button {
            width: 44px;
            height: 44px;
            padding: 0;
            font-size: 20px;
        }
        .back-btn {
            background: rgba(255,255,255,0.1);
            padding: 8px 16px;
            border-radius: 30px;
            font-size: 14px;
            margin-right: 12px;
        }
        .hidden { display: none; }
        .search-row { display: flex; gap: 8px; margin-bottom: 16px; }
        .small-btn {
            background: rgba(255,255,255,0.08);
            padding: 6px 14px;
            border-radius: 30px;
            font-size: 12px;
            cursor: pointer;
        }
        .flex-between { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .success, .error {
            padding: 8px;
            border-radius: 20px;
            text-align: center;
            font-size: 12px;
            margin-top: 10px;
            display: none;
        }
        .success { background: #10b981; }
        .error { background: #ef4444; }
    </style>
</head>
<body>
<div class="app" id="app">
    <!-- Страница входа -->
    <div id="loginPage" class="page active" style="display: flex; flex-direction: column; justify-content: center;">
        <div style="text-align: center; margin-bottom: 40px;">
            <div style="font-size: 64px; margin-bottom: 16px;">💎</div>
            <div style="font-size: 32px; font-weight: 700;">LUXA</div>
            <div style="font-size: 12px; opacity: 0.5;">PREMIUM MESSENGER</div>
        </div>
        <div style="margin-bottom: 16px;">
            <input type="tel" id="loginPhone" placeholder="Телефон">
        </div>
        <div style="margin-bottom: 16px;">
            <input type="text" id="loginName" placeholder="Имя">
        </div>
        <button id="doLoginBtn" style="margin-bottom: 20px;">ВОЙТИ</button>
        <div style="margin-bottom: 16px;">
            <input type="text" id="newNick" placeholder="Новый ник">
        </div>
        <button id="updateProfileBtn" style="background: transparent; border: 1px solid rgba(255,255,255,0.2);">ОБНОВИТЬ ПРОФИЛЬ</button>
        <div id="successMsg" class="success"></div>
        <div id="errorMsg" class="error"></div>
    </div>

    <!-- Основной интерфейс -->
    <div id="mainApp" style="display: none; flex-direction: column; flex: 1;">
        <div class="header">
            <div class="logo">LUXA</div>
            <div class="profile-badge" id="userNameDisplay"></div>
        </div>

        <div id="chatsPage" class="page active">
            <div class="flex-between">
                <div style="font-weight: 600;">💬 ЧАТЫ</div>
            </div>
            <div id="friendsList"></div>
        </div>

        <div id="contactsPage" class="page">
            <div class="search-row">
                <input type="text" id="searchInput" placeholder="Поиск по ID или имени">
                <button id="searchBtn" style="width: auto; padding: 12px 20px;">🔍</button>
            </div>
            <div id="searchResults"></div>
        </div>

        <div id="globalPage" class="page">
            <div style="font-weight: 600; margin-bottom: 16px;">🌍 ОБЩИЙ ЧАТ</div>
            <div id="globalMessages" style="flex:1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; height: 55vh;"></div>
            <div class="input-row">
                <input type="text" id="globalMsgInput" placeholder="Сообщение в общий чат...">
                <button id="globalSendBtn">➤</button>
            </div>
        </div>

        <div id="chatPage" class="page">
            <div style="display: flex; align-items: center; margin-bottom: 16px;">
                <button class="back-btn" id="closeChatBtn">← Назад</button>
                <div style="flex:1; text-align: center; font-weight: 600;" id="chatPartnerName"></div>
            </div>
            <div id="chatMessagesArea" style="flex:1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; height: 60vh;"></div>
            <div class="input-row">
                <input type="text" id="chatMsgInput" placeholder="Сообщение...">
                <button id="sendChatMsgBtn">➤</button>
            </div>
        </div>

        <div class="bottom-menu">
            <div class="menu-item active" data-page="chats">
                <div class="menu-icon">💬</div>
                <div class="menu-label">Чаты</div>
            </div>
            <div class="menu-item" data-page="contacts">
                <div class="menu-icon">👥</div>
                <div class="menu-label">Контакты</div>
            </div>
            <div class="menu-item" data-page="global">
                <div class="menu-icon">🌍</div>
                <div class="menu-label">Общий</div>
            </div>
        </div>
    </div>
</div>

<script>
    const API = window.location.origin;
    let currentUser = null;
    let activeChat = null;
    let currentFriends = [];
    let pollingInterval = null;
    let glbInterval = null;

    const loginPage = document.getElementById('loginPage');
    const mainApp = document.getElementById('mainApp');
    const friendsListDiv = document.getElementById('friendsList');
    const searchResultsDiv = document.getElementById('searchResults');
    const globalMessagesDiv = document.getElementById('globalMessages');
    const chatMessagesDiv = document.getElementById('chatMessagesArea');
    const chatPartnerName = document.getElementById('chatPartnerName');
    const userNameDisplay = document.getElementById('userNameDisplay');

    async function registerOrUpdate(phone, username) {
        const res = await fetch(`${API}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone, username })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.status === 'ok') return data.username;
        throw new Error('Ошибка');
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
            setTimeout(() => initApp(), 500);
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
            userNameDisplay.innerText = newName;
        } catch(e) { showError('Ошибка: ' + e.message); }
    };

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
            if (data.is_online) return '🟢 онлайн';
            if (isFriend && data.last_seen_text) return `⚫ ${data.last_seen_text}`;
            return '⚫ не в сети';
        } catch { return '⚫ ...'; }
    }

    async function loadFriends() {
        const res = await fetch(`${API}/friends/${currentUser.phone}`);
        const data = await res.json();
        currentFriends = data;
        return currentFriends;
    }

    async function renderChats() {
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
                            <div class="sub">${status}</div>
                        </div>
                        <div>💬</div>
                    </div>`;
        }
        friendsListDiv.innerHTML = html || '<div style="text-align:center; padding:40px;">➕ Добавьте друзей через вкладку "Контакты"</div>';
        document.querySelectorAll('.friend-card').forEach(card => {
            card.onclick = () => openChat(card.dataset.phone);
        });
    }

    document.getElementById('searchBtn').onclick = async () => {
        const query = document.getElementById('searchInput').value.trim();
        if (!query) return;
        const res = await fetch(`${API}/search_users?q=${encodeURIComponent(query)}`);
        const users = await res.json();
        const filtered = users.filter(u => u.phone !== currentUser.phone);
        let html = '';
        for (let u of filtered) {
            const isFriend = currentFriends.some(f => f.friend_phone === u.phone);
            html += `<div class="user-card" style="justify-content:space-between;">
                        <div style="display:flex; align-items:center; gap:14px;">
                            <div class="avatar">👤</div>
                            <div><strong>${escapeHtml(u.username)}</strong><br><small>${u.phone}</small></div>
                        </div>
                        ${!isFriend ? `<button class="small-btn" data-add="${u.phone}">➕ ДОБАВИТЬ</button>` : '<span style="opacity:0.5;">✓ друг</span>'}
                    </div>`;
        }
        searchResultsDiv.innerHTML = html || '<div style="text-align:center; padding:40px;">Ничего не найдено</div>';
        document.querySelectorAll('[data-add]').forEach(btn => {
            btn.onclick = async (e) => {
                const friendPhone = btn.dataset.add;
                await fetch(`${API}/add_friend`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_phone: currentUser.phone, friend_phone: friendPhone })
                });
                await renderChats();
                btn.remove();
            };
        });
    };

    async function loadGlobalMessages() {
        if (!globalMessagesDiv) return;
        const res = await fetch(`${API}/general_messages`);
        const data = await res.json();
        let html = '';
        for (let m of data.messages || []) {
            const isOut = m.from === currentUser.phone;
            html += `<div class="message-bubble ${isOut ? 'my-msg' : 'their-msg'}">${escapeHtml(m.text)}<div style="font-size:9px; opacity:0.5; margin-top:4px;">${new Date(m.time).toLocaleTimeString()}</div></div>`;
        }
        globalMessagesDiv.innerHTML = html;
        globalMessagesDiv.scrollTop = globalMessagesDiv.scrollHeight;
    }

    async function sendGlobalMessage(text) {
        await fetch(`${API}/send_general`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ from_phone: currentUser.phone, text, message_type: 'text' })
        });
        loadGlobalMessages();
    }

    document.getElementById('globalSendBtn').onclick = () => {
        const inp = document.getElementById('globalMsgInput');
        if (inp.value.trim()) sendGlobalMessage(inp.value.trim());
        inp.value = '';
    };

    async function openChat(phone) {
        activeChat = phone;
        const usersRes = await fetch(`${API}/users`);
        const users = await usersRes.json();
        const partner = users.find(u => u.phone === phone);
        chatPartnerName.innerText = partner ? partner.username : phone;
        switchPage('chat');
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
            div.className = `message-bubble ${isOut ? 'my-msg' : 'their-msg'}`;
            div.innerHTML = `${escapeHtml(m.text)}<div style="font-size:9px; opacity:0.5; margin-top:4px;">${new Date(m.time).toLocaleTimeString()}</div>`;
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

    document.getElementById('sendChatMsgBtn').onclick = () => {
        const inp = document.getElementById('chatMsgInput');
        if (inp.value.trim()) sendPrivateMessage(inp.value.trim());
        inp.value = '';
    };
    document.getElementById('closeChatBtn').onclick = () => {
        if (pollingInterval) clearInterval(pollingInterval);
        activeChat = null;
        switchPage('chats');
        renderChats();
    };

    function switchPage(pageId) {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`${pageId}Page`).classList.add('active');
        document.querySelectorAll('.menu-item').forEach(item => item.classList.remove('active'));
        document.querySelector(`.menu-item[data-page="${pageId}"]`).classList.add('active');
        if (pageId === 'chats') renderChats();
        if (pageId === 'global') loadGlobalMessages();
    }

    document.querySelectorAll('.menu-item').forEach(item => {
        item.onclick = () => switchPage(item.dataset.page);
    });

    async function initApp() {
        userNameDisplay.innerText = currentUser.username;
        loginPage.style.display = 'none';
        mainApp.style.display = 'flex';
        await renderChats();
        switchPage('chats');
        updateOnline();
        if (glbInterval) clearInterval(glbInterval);
        glbInterval = setInterval(loadGlobalMessages, 5000);
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
            initApp();
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
