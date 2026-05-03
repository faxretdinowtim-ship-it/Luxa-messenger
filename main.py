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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite+aiosqlite:///./luxa.db"
else:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

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
    is_read = Column(Boolean, default=False)

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
    print("✅ Сервер запущен")

HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes, viewport-fit=cover">
    <title>LUXA | GOLD PREMIUM</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        
        body {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Inter', system-ui, sans-serif;
            background: #03030a;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
            position: relative;
        }
        
        /* 3D КИНЕМАТОГРАФИЧНЫЙ ФОН */
        body::before {
            content: '';
            position: fixed;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: 
                radial-gradient(ellipse at 20% 25%, rgba(139, 92, 246, 0.25), transparent 70%),
                radial-gradient(ellipse at 85% 70%, rgba(99, 102, 241, 0.2), transparent 60%),
                repeating-linear-gradient(45deg, rgba(255,215,0,0.03) 0px, rgba(255,215,0,0.03) 2px, transparent 2px, transparent 12px);
            z-index: -2;
            animation: slowDrift 25s ease infinite;
        }
        
        @keyframes slowDrift {
            0%, 100% { transform: translate(0,0) scale(1); }
            50% { transform: translate(1%, -0.5%) scale(1.02); }
        }
        
        body::after {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(circle at 50% 50%, rgba(0,0,0,0) 0%, rgba(0,0,0,0.5) 100%);
            z-index: -1;
            pointer-events: none;
        }
        
        /* ПРЕМИУМ СТЕКЛЯННЫЙ КОНТЕЙНЕР */
        .app {
            width: 100%;
            max-width: 480px;
            height: 95vh;
            max-height: 820px;
            background: rgba(12, 12, 25, 0.65);
            backdrop-filter: blur(35px) saturate(180%);
            border-radius: 56px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 40px 70px -30px rgba(0,0,0,0.6), 0 0 0 1.5px rgba(255,215,0,0.15), inset 0 1px 0 rgba(255,255,255,0.05);
            animation: fadeUp 0.5s cubic-bezier(0.2,0.9,0.4,1.1);
        }
        
        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(30px) scale(0.96); backdrop-filter: blur(0px); }
            to { opacity: 1; transform: translateY(0) scale(1); backdrop-filter: blur(35px) saturate(180%); }
        }
        
        /* СТРАНИЦЫ */
        .page {
            flex: 1;
            overflow-y: auto;
            padding: 24px 20px;
            display: none;
            animation: pageEnter 0.35s ease;
        }
        .page.active { display: block; }
        @keyframes pageEnter {
            from { opacity: 0; transform: translateX(20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        /* ЗОЛОТОЕ НИЖНЕЕ МЕНЮ */
        .gold-menu {
            background: rgba(10, 10, 20, 0.85);
            backdrop-filter: blur(30px);
            display: flex;
            justify-content: space-around;
            padding: 12px 16px 22px;
            border-top: 0.5px solid rgba(255,215,0,0.2);
        }
        .menu-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
            cursor: pointer;
            padding: 8px 16px;
            border-radius: 40px;
            transition: all 0.25s cubic-bezier(0.2,0.9,0.4,1.1);
        }
        .menu-item.active {
            background: rgba(255,215,0,0.15);
            transform: translateY(-2px);
        }
        .menu-icon { font-size: 26px; }
        .menu-label {
            font-size: 11px;
            font-weight: 600;
            color: rgba(255,255,255,0.5);
        }
        .menu-item.active .menu-label {
            color: #FFD700;
            text-shadow: 0 0 8px rgba(255,215,0,0.5);
        }
        
        /* ПРЕМИУМ ХЕДЕР */
        .premium-header {
            padding: 18px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 0.5px solid rgba(255,215,0,0.15);
            background: rgba(0,0,0,0.2);
        }
        .logo-gold {
            font-size: 22px;
            font-weight: 800;
            background: linear-gradient(135deg, #FFD700, #FFA500, #FFD700);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            letter-spacing: -0.5px;
        }
        .profile-gold {
            background: rgba(255,215,0,0.1);
            padding: 6px 14px;
            border-radius: 40px;
            font-size: 13px;
            font-weight: 600;
            color: #FFD700;
            border: 0.5px solid rgba(255,215,0,0.3);
        }
        
        /* ЯРКИЕ КАРТОЧКИ ДРУЗЕЙ И ЧАТОВ */
        .friend-card, .user-card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 28px;
            padding: 14px 18px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 16px;
            cursor: pointer;
            border: 0.5px solid rgba(255,215,0,0.2);
            transition: all 0.25s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .friend-card:hover { transform: translateX(5px); border-color: rgba(255,215,0,0.5); }
        .friend-card:active { transform: scale(0.98); }
        
        .avatar-gold {
            width: 54px; height: 54px;
            background: linear-gradient(145deg, #7C3AED, #4F46E5);
            border-radius: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            box-shadow: 0 8px 16px -6px rgba(0,0,0,0.4);
        }
        .info-gold { flex: 1; }
        .name-gold { font-weight: 700; font-size: 17px; color: #FFE4B5; letter-spacing: -0.2px; }
        .sub-gold { font-size: 12px; opacity: 0.7; margin-top: 4px; color: rgba(255,255,255,0.7); }
        
        /* 3D СООБЩЕНИЯ С ЭФФЕКТОМ СВЕЧЕНИЯ */
        .message-bubble {
            max-width: 80%;
            padding: 12px 18px;
            border-radius: 28px;
            font-size: 15px;
            margin-bottom: 8px;
            animation: messageGlow 0.3s ease-out;
            position: relative;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        @keyframes messageGlow {
            from { opacity: 0; transform: translateY(12px) scale(0.96); filter: blur(2px); }
            to { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
        }
        .my-msg {
            background: linear-gradient(135deg, #8B5CF6, #6366F1);
            align-self: flex-end;
            border-bottom-right-radius: 6px;
            color: white;
            box-shadow: 0 0 12px rgba(139,92,246,0.4);
        }
        .their-msg {
            background: rgba(30,30,45,0.8);
            backdrop-filter: blur(12px);
            align-self: flex-start;
            border-bottom-left-radius: 6px;
            color: #f0f0ff;
            border: 0.5px solid rgba(255,215,0,0.2);
        }
        .msg-status {
            font-size: 9px;
            opacity: 0.6;
            margin-top: 5px;
            text-align: right;
            display: flex;
            gap: 6px;
            justify-content: flex-end;
        }
        .msg-time { font-size: 9px; opacity: 0.5; }
        .delivered { color: #4ade80; }
        .read { color: #FFD700; }
        
        /* ПРЕМИУМ ПОЛЕ ВВОДА */
        .input-luxury {
            display: flex;
            gap: 10px;
            background: rgba(255,255,255,0.05);
            border-radius: 60px;
            padding: 6px 6px 6px 22px;
            margin: 12px;
            border: 0.5px solid rgba(255,215,0,0.2);
            backdrop-filter: blur(10px);
        }
        .input-luxury input {
            flex: 1;
            background: transparent;
            border: none;
            padding: 14px 0;
            color: white;
            font-size: 15px;
            outline: none;
        }
        .input-luxury button {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #8B5CF6, #6366F1);
            border-radius: 50px;
            padding: 0;
            font-size: 22px;
            margin: 0;
            box-shadow: 0 0 10px rgba(99,102,241,0.4);
        }
        
        /* ДРУГИЕ ЭЛЕМЕНТЫ */
        input, button { width: 100%; }
        input {
            padding: 16px 18px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,215,0,0.2);
            border-radius: 48px;
            color: white;
            font-size: 15px;
            outline: none;
        }
        button {
            background: linear-gradient(135deg, #8B5CF6, #6366F1);
            border: none;
            border-radius: 48px;
            padding: 16px;
            color: white;
            font-weight: 700;
            font-size: 16px;
            cursor: pointer;
            margin-top: 12px;
        }
        .search-row { display: flex; gap: 10px; margin-bottom: 20px; }
        .small-btn {
            background: rgba(255,215,0,0.15);
            padding: 6px 14px;
            border-radius: 30px;
            font-size: 12px;
            cursor: pointer;
            color: #FFD700;
        }
        .back-gold {
            background: rgba(255,215,0,0.1);
            padding: 8px 18px;
            border-radius: 40px;
            font-size: 14px;
            color: #FFD700;
        }
        .success, .error {
            padding: 12px;
            border-radius: 40px;
            text-align: center;
            margin-top: 12px;
            display: none;
        }
        .success { background: #10b981; }
        .error { background: #ef4444; }
        .flex-between { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
        .scroll-area { height: 55vh; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
        .hidden { display: none; }
        
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
        ::-webkit-scrollbar-thumb { background: #FFD700; border-radius: 10px; }
    </style>
</head>
<body>
<div class="app" id="app">
    <!-- ЛОГИН -->
    <div id="loginPage" class="page active" style="display: flex; flex-direction: column; justify-content: center;">
        <div style="text-align: center; margin-bottom: 40px;">
            <div style="font-size: 70px; margin-bottom: 12px; text-shadow: 0 0 20px #FFD700;">💎</div>
            <div style="font-size: 34px; font-weight: 800; background: linear-gradient(135deg, #FFD700, #FFA500); -webkit-background-clip: text; background-clip: text; color: transparent;">LUXA</div>
            <div style="font-size: 11px; letter-spacing: 2px; color: rgba(255,215,0,0.6);">GOLD PREMIUM</div>
        </div>
        <input type="tel" id="loginPhone" placeholder="ТЕЛЕФОН" style="margin-bottom: 12px;">
        <input type="text" id="loginName" placeholder="ИМЯ" style="margin-bottom: 20px;">
        <button id="doLoginBtn">ВОЙТИ В LUXA</button>
        <input type="text" id="newNick" placeholder="НОВЫЙ НИК" style="margin-top: 20px;">
        <button id="updateProfileBtn" style="background: transparent; border: 1px solid rgba(255,215,0,0.4);">ОБНОВИТЬ ПРОФИЛЬ</button>
        <div id="successMsg" class="success"></div>
        <div id="errorMsg" class="error"></div>
    </div>

    <!-- ОСНОВНОЙ ИНТЕРФЕЙС -->
    <div id="mainApp" style="display: none; flex-direction: column; flex: 1;">
        <div class="premium-header">
            <div class="logo-gold">LUXA GOLD</div>
            <div class="profile-gold" id="userNameDisplay"></div>
        </div>

        <div id="chatsPage" class="page active">
            <div class="flex-between"><div style="font-weight: 700; color: #FFD700;">💎 VIP ЧАТЫ</div></div>
            <div id="friendsList"></div>
        </div>

        <div id="contactsPage" class="page">
            <div class="search-row"><input type="text" id="searchInput" placeholder="🔍 ПОИСК ПО ID"><button id="searchBtn" style="width: auto; padding: 0 20px;">ИСКАТЬ</button></div>
            <div id="searchResults"></div>
        </div>

        <div id="globalPage" class="page">
            <div style="font-weight: 700; color: #FFD700; margin-bottom: 16px;">🌍 ОБЩИЙ ЧАТ</div>
            <div id="globalMessages" class="scroll-area"></div>
            <div class="input-luxury"><input type="text" id="globalMsgInput" placeholder="Сообщение..."><button id="globalSendBtn">➤</button></div>
        </div>

        <div id="chatPage" class="page">
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
                <button class="back-gold" id="closeChatBtn">← НАЗАД</button>
                <div style="flex:1; text-align: center; font-weight: 700; font-size: 18px; color: #FFD700;" id="chatPartnerName"></div>
            </div>
            <div id="chatMessagesArea" class="scroll-area" style="height: 60vh;"></div>
            <div class="input-luxury"><input type="text" id="chatMsgInput" placeholder="Сообщение..."><button id="sendChatMsgBtn">➤</button></div>
        </div>

        <div class="gold-menu">
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
        await fetch(`${API}/update_status`,{ method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ phone:currentUser.phone }) });
    }
    setInterval(updateOnline,20000);
    
    async function getStatus(phone, isFriend){
        try{
            const url = isFriend ? `${API}/get_status/${phone}?viewer_phone=${currentUser.phone}` : `${API}/get_status/${phone}`;
            const r=await fetch(url); const d=await r.json();
            if(d.is_online) return '🟢 ОНЛАЙН';
            if(isFriend && d.last_seen_text) return `⚫ ${d.last_seen_text}`;
            return '⚫ НЕ В СЕТИ';
        }catch(e){ return '⚫ ...'; }
    }

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
            const status=await getStatus(f.friend_phone,true);
            html+=`<div class="friend-card" data-phone="${f.friend_phone}"><div class="avatar-gold">👤</div><div class="info-gold"><div class="name-gold">${escapeHtml(name)}</div><div class="sub-gold">${status}</div></div><div>💬</div></div>`;
        }
        document.getElementById('friendsList').innerHTML = html || '<div style="text-align:center; padding:40px;">➕ Добавьте друзей в "КОНТАКТЫ"</div>';
        document.querySelectorAll('.friend-card').forEach(c=>c.onclick=()=>openChat(c.dataset.phone));
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
            html+=`<div class="user-card" style="justify-content:space-between;"><div style="display:flex; gap:14px;"><div class="avatar-gold">👤</div><div><strong>${escapeHtml(u.username)}</strong><br><small>${u.phone}</small></div></div>${!isFriend?`<button class="small-btn" data-add="${u.phone}">➕ ДОБАВИТЬ</button>`:'<span style="color:#FFD700;">✓ friend</span>'}</div>`;
        }
        document.getElementById('searchResults').innerHTML = html || '<div style="text-align:center; padding:40px;">Не найдено</div>';
        document.querySelectorAll('[data-add]').forEach(btn=>btn.onclick=async e=>{
            const fPhone=btn.dataset.add;
            await fetch(`${API}/add_friend`,{ method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ user_phone:currentUser.phone, friend_phone:fPhone }) });
            await renderChats(); btn.remove();
        });
    };

    async function loadGlobal(){
        const r=await fetch(`${API}/general_messages`); const d=await r.json();
        let html='';
        for(let m of d.messages||[]){
            const isOut=m.from===currentUser.phone;
            html+=`<div class="message-bubble ${isOut?'my-msg':'their-msg'}">${escapeHtml(m.text)}<div class="msg-status"><span class="msg-time">${new Date(m.time).toLocaleTimeString()}</span><span class="delivered">✓ доставлено</span></div></div>`;
        }
        document.getElementById('globalMessages').innerHTML=html;
        document.getElementById('globalMessages').scrollTop=document.getElementById('globalMessages').scrollHeight;
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
        pollingChat=setInterval(loadPrivate,3500);
    }

    async function loadPrivate(){
        if(!activeChat) return;
        const r=await fetch(`${API}/dialog/${currentUser.phone}/${activeChat}`); const d=await r.json();
        const wasBottom=document.getElementById('chatMessagesArea').scrollHeight-document.getElementById('chatMessagesArea').scrollTop-document.getElementById('chatMessagesArea').clientHeight<50;
        let html='';
        for(let m of d.messages||[]){
            const isOut=m.from===currentUser.phone;
            html+=`<div class="message-bubble ${isOut?'my-msg':'their-msg'}">${escapeHtml(m.text)}<div class="msg-status"><span class="msg-time">${new Date(m.time).toLocaleTimeString()}</span><span class="delivered">✓ доставлено</span></div></div>`;
        }
        document.getElementById('chatMessagesArea').innerHTML=html;
        if(wasBottom) document.getElementById('chatMessagesArea').scrollTop=document.getElementById('chatMessagesArea').scrollHeight;
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
        glbInt=setInterval(loadGlobal,4500);
    }

    function escapeHtml(s){ if(!s) return ''; return s.replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]); }

    const saved=localStorage.getItem('luxa_user');
    if(saved){
        try{ currentUser=JSON.parse(saved); document.getElementById('loginPhone').value=currentUser.phone; document.getElementById('loginName').value=currentUser.username; initApp(); }catch(e){}
    }
</script>
</body>
</html>
"""

@app.get("/")
@app.get("/web")
async def serve_index():
    return HTMLResponse(content=HTML_PAGE)

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
        if diff.days > 0: last_text = f"{diff.days} дн. назад"
        elif diff.seconds > 3600: last_text = f"{diff.seconds // 3600} ч. назад"
        elif diff.seconds > 60: last_text = f"{diff.seconds // 60} мин. назад"
        else: last_text = "только что"
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
