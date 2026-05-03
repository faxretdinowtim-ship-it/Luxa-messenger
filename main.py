from fastapi import FastAPI, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
import json
import re
import uvicorn
from datetime import datetime

app = FastAPI(title="LUXA Messenger", description="Премиальный мессенджер с админ-панелью")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Админ авторизация
security = HTTPBasic()
ADMIN_PASSWORD = "2503"  # Пароль изменён

# Файл для хранения кастомных стилей
CUSTOM_CSS_FILE = "custom_style.json"
STYLES_HISTORY_FILE = "styles_history.json"

def load_custom_css():
    try:
        with open(CUSTOM_CSS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"css": "", "history": [], "version": 1}

def save_custom_css(css_data):
    with open(CUSTOM_CSS_FILE, "w", encoding="utf-8") as f:
        json.dump(css_data, f, ensure_ascii=False, indent=2)

def get_base_html():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return get_default_html()

def get_default_html():
    return """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes, viewport-fit=cover">
    <title>LUXA — Premium Messenger</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Inter', system-ui, sans-serif; background: #050508; min-height: 100vh; display: flex; justify-content: center; align-items: center; position: relative; overflow: hidden; }
        body::before { content: ''; position: fixed; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(ellipse at 20% 25%, rgba(139, 92, 246, 0.15), transparent 70%); z-index: -2; }
        .app { width: 100%; max-width: 460px; height: 94vh; max-height: 800px; background: rgba(10, 10, 20, 0.7); backdrop-filter: blur(30px); border-radius: 52px; overflow: hidden; display: flex; flex-direction: column; box-shadow: 0 35px 65px -25px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.06); }
        .screen { flex: 1; display: flex; flex-direction: column; padding: 28px 22px; overflow-y: auto; }
        .hidden { display: none !important; }
        .logo-block { text-align: center; margin-bottom: 40px; }
        .logo-icon { width: 80px; height: 80px; background: linear-gradient(145deg, #FFFFFF, #E2E2FF); border-radius: 35px; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; font-size: 44px; }
        .logo-text { font-size: 34px; font-weight: 800; letter-spacing: -1.5px; background: linear-gradient(135deg, #FFFFFF 20%, #C4B5FD 60%); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .logo-sub { font-size: 11px; letter-spacing: 2px; color: rgba(255,255,255,0.45); }
        .input-field { margin-bottom: 20px; }
        .input-label { font-size: 12px; font-weight: 600; margin-bottom: 8px; color: rgba(255,255,255,0.6); padding-left: 14px; }
        input { width: 100%; padding: 18px 22px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 44px; color: white; font-size: 16px; outline: none; }
        input:focus { border-color: #8B5CF6; background: rgba(255,255,255,0.08); }
        .btn-primary { width: 100%; padding: 18px; background: linear-gradient(105deg, #7C3AED, #6366F1); border: none; border-radius: 48px; color: white; font-weight: 700; font-size: 17px; cursor: pointer; }
        .status-group { display: flex; gap: 12px; margin-top: 20px; background: rgba(255,255,255,0.03); padding: 5px; border-radius: 60px; }
        .status-chip { flex: 1; text-align: center; padding: 10px; border-radius: 50px; font-size: 13px; color: rgba(255,255,255,0.5); cursor: pointer; }
        .status-chip.active { background: rgba(124, 58, 237, 0.35); color: white; }
        .chat-card { background: rgba(255,255,255,0.04); margin-bottom: 14px; border-radius: 32px; padding: 12px 16px; display: flex; align-items: center; gap: 16px; cursor: pointer; border: 0.5px solid rgba(255,255,255,0.05); }
        .avatar { width: 58px; height: 58px; background: linear-gradient(145deg, #4F46E5, #6D28D9); border-radius: 32px; display: flex; align-items: center; justify-content: center; font-size: 30px; }
        .chat-info { flex: 1; }
        .chat-name { font-weight: 700; font-size: 17px; }
        .chat-preview { font-size: 12px; opacity: 0.6; }
        .chat-header { display: flex; align-items: center; gap: 16px; margin-bottom: 22px; padding-bottom: 14px; border-bottom: 0.5px solid rgba(255,255,255,0.08); }
        .back-btn { width: 44px; height: 44px; background: rgba(255,255,255,0.06); border: none; border-radius: 30px; font-size: 24px; cursor: pointer; }
        .messages-area { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding: 8px 4px 20px; }
        .message { max-width: 80%; padding: 12px 18px; border-radius: 28px; font-size: 15px; animation: messageSlide 0.3s ease; }
        @keyframes messageSlide { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .my-message { background: #7C3AED; align-self: flex-end; border-bottom-right-radius: 8px; color: white; }
        .their-message { background: rgba(255,255,255,0.08); align-self: flex-start; border-bottom-left-radius: 8px; color: white; }
        .message-time { font-size: 9px; opacity: 0.55; margin-top: 5px; text-align: right; }
        .typing-bubble { display: flex; align-items: center; gap: 8px; background: rgba(255,255,255,0.08); width: fit-content; padding: 10px 18px; border-radius: 30px; }
        .dot { width: 6px; height: 6px; background: #A78BFA; border-radius: 50%; animation: typingPulse 1.2s infinite; }
        @keyframes typingPulse { 0%, 60%, 100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-5px); opacity: 1; } }
        .input-bar { display: flex; gap: 12px; background: rgba(255,255,255,0.04); border-radius: 50px; padding: 6px 6px 6px 22px; }
        .input-bar input { background: transparent; border: none; padding: 14px 0; }
        .input-bar button { width: 50px; height: 50px; background: #7C3AED; border-radius: 40px; font-size: 22px; }
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
        ::-webkit-scrollbar-thumb { background: #7C3AED; border-radius: 10px; }
    </style>
</head>
<body>
<div class="app" id="app">...</div>
</body>
</html>"""

def inject_custom_css(html_content, custom_css):
    if not custom_css:
        return html_content
    pattern = r'(</style>)'
    replacement = custom_css + r'\n</style>'
    return re.sub(pattern, replacement, html_content, count=1, flags=re.DOTALL)

@app.get("/")
@app.get("/web")
async def root():
    html = get_base_html()
    custom_data = load_custom_css()
    if custom_data.get("css"):
        html = inject_custom_css(html, custom_data["css"])
    return HTMLResponse(content=html)

# ========== АДМИН-ПАНЕЛЬ (пароль 2503) ==========

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LUXA Admin — Редактор дизайна</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', system-ui, sans-serif;
            background: linear-gradient(135deg, #0a0a1a, #0f0f1f);
            min-height: 100vh;
            padding: 40px 20px;
            color: #fff;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { font-size: 32px; font-weight: 700; margin-bottom: 8px; background: linear-gradient(135deg, #fff, #a78bfa); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .sub { color: rgba(255,255,255,0.5); margin-bottom: 30px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
        .card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 28px;
            padding: 24px;
            border: 0.5px solid rgba(255,255,255,0.1);
        }
        .card h3 { font-size: 20px; font-weight: 600; margin-bottom: 16px; }
        textarea {
            width: 100%;
            min-height: 400px;
            background: rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 20px;
            color: #d4d4d4;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
            resize: vertical;
        }
        .btn {
            background: linear-gradient(105deg, #7C3AED, #6366F1);
            border: none;
            border-radius: 40px;
            padding: 14px 28px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            margin-top: 16px;
            margin-right: 12px;
            transition: 0.2s;
        }
        .btn-secondary { background: rgba(255,255,255,0.1); }
        .btn:hover { transform: translateY(-2px); }
        .preview {
            background: rgba(0,0,0,0.3);
            border-radius: 20px;
            padding: 16px;
            margin-top: 16px;
            font-size: 12px;
            font-family: monospace;
            max-height: 200px;
            overflow: auto;
        }
        .success { color: #4ade80; margin-top: 12px; }
        .error { color: #f87171; margin-top: 12px; }
        .preset-btns { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
        .preset-btn {
            background: rgba(255,255,255,0.08);
            border: none;
            border-radius: 40px;
            padding: 8px 18px;
            color: #a78bfa;
            cursor: pointer;
            font-size: 13px;
        }
        .history-item {
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 12px;
            margin-bottom: 10px;
        }
        .history-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .history-name { font-weight: 600; }
        .history-time { font-size: 11px; opacity: 0.5; }
        .history-preview { font-size: 11px; opacity: 0.6; margin-bottom: 8px; }
        .restore-btn { background: rgba(255,255,255,0.1); border: none; border-radius: 30px; padding: 6px 14px; color: #a78bfa; cursor: pointer; font-size: 12px; }
        input, select {
            width: 100%;
            padding: 14px 18px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 24px;
            color: white;
            margin-bottom: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 LUXA Admin Panel</h1>
        <div class="sub">Редактирование дизайна — пароль: 2503</div>
        
        <div class="grid">
            <div class="card">
                <h3>📝 Редактор CSS</h3>
                <div class="preset-btns">
                    <button class="preset-btn" onclick="loadPreset('glass')">Стекло</button>
                    <button class="preset-btn" onclick="loadPreset('neon')">Неон</button>
                    <button class="preset-btn" onclick="loadPreset('dark')">Тёмный</button>
                    <button class="preset-btn" onclick="loadPreset('luxury')">Золотой</button>
                    <button class="preset-btn" onclick="loadPreset('reset')">Сброс</button>
                </div>
                <textarea id="cssEditor" placeholder="Введите свой CSS код..."></textarea>
                <button class="btn" onclick="saveCSS()">💾 Сохранить изменения</button>
                <button class="btn btn-secondary" onclick="previewCSS()">👁 Предпросмотр</button>
                <div id="statusMsg" class="success"></div>
            </div>
            
            <div class="card">
                <h3>📦 История изменений</h3>
                <div id="historyList" style="max-height: 400px; overflow-y: auto;">
                    <div style="color: rgba(255,255,255,0.4); text-align: center;">Загрузка...</div>
                </div>
            </div>
        </div>
        
        <div class="card" style="margin-top: 24px;">
            <h3>🔧 Быстрые ссылки</h3>
            <button class="btn" onclick="window.open('/web', '_blank')">📱 Открыть мессенджер</button>
            <button class="btn btn-secondary" onclick="location.reload()">🔄 Обновить</button>
        </div>
    </div>

    <script>
        let saveTimeout = null;
        
        async function saveCSS() {
            const css = document.getElementById('cssEditor').value;
            const password = prompt('Введите пароль администратора (2503):');
            if (!password) return;
            
            const formData = new FormData();
            formData.append('css', css);
            formData.append('password', password);
            
            try {
                const res = await fetch('/admin/save_css', { method: 'POST', body: formData });
                const data = await res.json();
                const msgDiv = document.getElementById('statusMsg');
                if (res.ok) {
                    msgDiv.innerHTML = '✅ Дизайн сохранён! Обновите страницу мессенджера.';
                    msgDiv.style.color = '#4ade80';
                    loadHistory();
                    setTimeout(() => { msgDiv.innerHTML = ''; }, 3000);
                } else {
                    msgDiv.innerHTML = '❌ ' + data.detail;
                    msgDiv.style.color = '#f87171';
                }
            } catch(e) {
                alert('Ошибка: ' + e.message);
            }
        }
        
        async function previewCSS() {
            const css = document.getElementById('cssEditor').value;
            const win = window.open();
            win.document.write('<html><head><title>LUXA Preview</title><style>' + css + '</style></head><body style="margin:0;"><iframe src="/web" style="width:100%;height:100vh;border:none;"></iframe></body></html>');
        }
        
        async function loadHistory() {
            try {
                const res = await fetch('/admin/history');
                const data = await res.json();
                const historyDiv = document.getElementById('historyList');
                if (data.history && data.history.length > 0) {
                    historyDiv.innerHTML = data.history.map(item => `
                        <div class="history-item">
                            <div class="history-header">
                                <span class="history-name">${escapeHtml(item.name)}</span>
                                <span class="history-time">${item.timestamp}</span>
                            </div>
                            <div class="history-preview">${escapeHtml(item.preview)}</div>
                            <button class="restore-btn" onclick="restoreVersion(${item.id})">↩️ Восстановить</button>
                        </div>
                    `).join('');
                } else {
                    historyDiv.innerHTML = '<div style="text-align:center; opacity:0.5;">История пуста</div>';
                }
            } catch(e) {}
        }
        
        async function restoreVersion(id) {
            const password = prompt('Введите пароль администратора (2503):');
            if (!password) return;
            const formData = new FormData();
            formData.append('version_id', id);
            formData.append('password', password);
            try {
                const res = await fetch('/admin/restore', { method: 'POST', body: formData });
                const data = await res.json();
                if (res.ok) {
                    alert(data.message);
                    await loadCurrentCSS();
                    await loadHistory();
                } else {
                    alert('Ошибка: ' + data.detail);
                }
            } catch(e) {
                alert('Ошибка: ' + e.message);
            }
        }
        
        async function loadCurrentCSS() {
            try {
                const res = await fetch('/admin/current_css');
                const data = await res.json();
                document.getElementById('cssEditor').value = data.css || '';
            } catch(e) {}
        }
        
        function loadPreset(type) {
            const presets = {
                glass: `/* Премиум стекло */
.app { background: rgba(20, 20, 40, 0.55); backdrop-filter: blur(40px); }
.message { border-radius: 30px; }
.my-message { background: linear-gradient(135deg, #667eea, #764ba2); }
.their-message { background: rgba(255,255,255,0.1); }`,
                neon: `/* Неоновый стиль */
.my-message { background: #ff00ff; box-shadow: 0 0 15px #ff00ff; }
.their-message { background: #00ffff; box-shadow: 0 0 10px #00ffff; color: black; }
.chat-card:hover { box-shadow: 0 0 15px rgba(0,255,255,0.3); }
.btn-primary, .input-bar button { background: linear-gradient(105deg, #ff00ff, #00ffff); }`,
                dark: `/* Ультра-тёмный */
body { background: #000; }
.app { background: rgba(0,0,0,0.85); }
.my-message { background: #1a1a2e; border: 1px solid #333; }
.their-message { background: #0d0d1a; }
.chat-card { background: rgba(255,255,255,0.02); }`,
                luxury: `/* Золотой люкс */
.my-message { background: linear-gradient(135deg, #FFD700, #FFA500); color: #1a1a2e; font-weight: bold; }
.logo-text { background: linear-gradient(135deg, #FFD700, #FFA500); -webkit-background-clip: text; }
.btn-primary, .input-bar button { background: linear-gradient(135deg, #FFD700, #FFA500); color: #1a1a2e; }
.avatar { background: linear-gradient(145deg, #FFD700, #FFA500); }`,
                reset: ``
            };
            document.getElementById('cssEditor').value = presets[type] || '';
        }
        
        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[m]);
        }
        
        loadCurrentCSS();
        loadHistory();
    </script>
</body>
</html>
"""

@app.get("/admin")
async def admin_panel():
    return HTMLResponse(content=ADMIN_HTML)

@app.post("/admin/save_css")
async def save_css(
    css: str = Form(...),
    password: str = Form(...)
):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Неверный пароль")
    
    custom_data = load_custom_css()
    history = custom_data.get("history", [])
    
    # Сохраняем версию в историю
    history.insert(0, {
        "id": len(history) + 1,
        "name": f"Версия от {datetime.now().strftime('%H:%M:%S %d.%m')}",
        "timestamp": datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
        "preview": css[:150] + "..." if len(css) > 150 else css
    })
    
    # Ограничиваем историю 20 версиями
    if len(history) > 20:
        history = history[:20]
    
    custom_data["css"] = css
    custom_data["history"] = history
    custom_data["version"] = custom_data.get("version", 0) + 1
    save_custom_css(custom_data)
    
    return {"status": "ok", "message": "CSS сохранён"}

@app.get("/admin/current_css")
async def get_current_css():
    custom_data = load_custom_css()
    return {"css": custom_data.get("css", "")}

@app.get("/admin/history")
async def get_history():
    custom_data = load_custom_css()
    return {"history": custom_data.get("history", [])}

@app.post("/admin/restore")
async def restore_version(
    version_id: int = Form(...),
    password: str = Form(...)
):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Неверный пароль")
    
    custom_data = load_custom_css()
    history = custom_data.get("history", [])
    version = next((v for v in history if v["id"] == version_id), None)
    
    if not version:
        raise HTTPException(status_code=404, detail="Версия не найдена")
    
    return {"status": "ok", "message": f"Версия '{version['name']}' выбрана. Скопируйте CSS из истории для восстановления"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "LUXA", "version": "2.0"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
