from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
import asyncio
import uuid
import base64
import json
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import os
from ai_browser import create_ai_session, execute_ai_command, ai_sessions

app = FastAPI(
    title="🔨 𝙃𝘼𝙈𝙈𝙀𝙍 𝘼𝙐𝙏𝙊𝙈𝘼𝙏𝙄𝙊𝙉 𝘼𝙄",
    description="𝙋𝙧𝙤𝙛𝙚𝙨𝙨𝙞𝙤𝙣𝙖𝙡 𝘼𝙄-𝙋𝙤𝙬𝙚𝙧𝙚𝙙 𝘽𝙧𝙤𝙬𝙨𝙚𝙧 𝘼𝙪𝙩𝙤𝙢𝙖𝙩𝙞𝙤𝙣 𝙎𝙚𝙧𝙫𝙞𝙘𝙚",
    version="5.0.0"
)

active_sessions: Dict[str, Dict[str, Any]] = {}
playwright_instance = None
browser: Optional[Browser] = None
live_connections: List[Any] = []

class AutomationRequest(BaseModel):
    action: str = Field(description="Action: create, navigate, click, type, screenshot, execute, get_content, close, ai_command")
    session_id: Optional[str] = None
    url: Optional[str] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    script: Optional[str] = None
    full_page: bool = Field(default=False)
    wait_time: Optional[int] = Field(default=1000)
    ai_prompt: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    direction: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    global playwright_instance, browser
    playwright_instance = await async_playwright().start()
    browser = await playwright_instance.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled'
        ]
    )

@app.on_event("shutdown")
async def shutdown_event():
    global browser, playwright_instance
    for session_id in list(active_sessions.keys()):
        await close_session_internal(session_id)
    if browser:
        await browser.close()
    if playwright_instance:
        await playwright_instance.stop()

async def close_session_internal(session_id: str):
    if session_id in active_sessions:
        session = active_sessions[session_id]
        try:
            if session.get('page'):
                await session['page'].close()
            if session.get('context'):
                await session['context'].close()
        except:
            pass
        del active_sessions[session_id]

def get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"❌ Session {session_id} not found")
    return active_sessions[session_id]

async def inject_stealth_scripts(page: Page):
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        window.chrome = {
            runtime: {}
        };
    """)

async def broadcast_event(event_data: dict):
    for connection in live_connections[:]:
        try:
            await connection.send_json(event_data)
        except:
            live_connections.remove(connection)

@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔨 𝙃𝘼𝙈𝙈𝙀𝙍 𝘼𝙐𝙏𝙊𝙈𝘼𝙏𝙄𝙊𝙉 𝘼𝙄</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            @keyframes gradient {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
            
            @keyframes glow {
                0%, 100% { text-shadow: 0 0 10px #00ff00, 0 0 20px #00ff00, 0 0 30px #00ff00; }
                50% { text-shadow: 0 0 20px #00ff00, 0 0 30px #00ff00, 0 0 40px #00ff00, 0 0 50px #00ff00; }
            }
            
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #000000;
                color: #00ff00;
                min-height: 100vh;
                overflow-x: hidden;
            }
            
            .bg-animation {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(45deg, #000000, #0a0a0a, #001100, #000000);
                background-size: 400% 400%;
                animation: gradient 15s ease infinite;
                z-index: -1;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .header {
                text-align: center;
                padding: 40px 20px;
                border-bottom: 2px solid #00ff00;
                margin-bottom: 40px;
            }
            
            .logo {
                font-size: 120px;
                animation: pulse 2s ease-in-out infinite;
                margin-bottom: 20px;
            }
            
            .title {
                font-size: 3em;
                font-weight: bold;
                letter-spacing: 3px;
                animation: glow 2s ease-in-out infinite;
                margin-bottom: 15px;
                background: linear-gradient(90deg, #00ff00, #00ff88, #00ffff, #00ff88, #00ff00);
                background-size: 200% auto;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: gradient 3s linear infinite, glow 2s ease-in-out infinite;
            }
            
            .subtitle {
                font-size: 1.3em;
                color: #00ff88;
                text-shadow: 0 0 10px #00ff88;
                margin-bottom: 20px;
            }
            
            .telegram-link {
                display: inline-block;
                padding: 15px 30px;
                background: linear-gradient(135deg, #00ff00, #00ff88);
                color: #000;
                text-decoration: none;
                border-radius: 50px;
                font-weight: bold;
                font-size: 1.2em;
                transition: all 0.3s;
                box-shadow: 0 0 20px #00ff00;
                margin-top: 20px;
            }
            
            .telegram-link:hover {
                transform: scale(1.1);
                box-shadow: 0 0 30px #00ff00, 0 0 40px #00ff00;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 40px 0;
            }
            
            .stat-card {
                background: rgba(0, 255, 0, 0.05);
                border: 2px solid #00ff00;
                border-radius: 15px;
                padding: 30px;
                text-align: center;
                transition: all 0.3s;
                box-shadow: 0 0 20px rgba(0, 255, 0, 0.2);
            }
            
            .stat-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 0 30px rgba(0, 255, 0, 0.4);
                background: rgba(0, 255, 0, 0.1);
            }
            
            .stat-number {
                font-size: 3em;
                font-weight: bold;
                color: #00ff00;
                text-shadow: 0 0 20px #00ff00;
            }
            
            .stat-label {
                font-size: 1.1em;
                color: #00ff88;
                margin-top: 10px;
            }
            
            .features-section {
                margin: 40px 0;
            }
            
            .section-title {
                font-size: 2.5em;
                text-align: center;
                margin-bottom: 30px;
                color: #00ff00;
                text-shadow: 0 0 20px #00ff00;
            }
            
            .features-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }
            
            .feature-card {
                background: rgba(0, 255, 0, 0.05);
                border: 2px solid #00ff00;
                border-radius: 15px;
                padding: 25px;
                transition: all 0.3s;
            }
            
            .feature-card:hover {
                background: rgba(0, 255, 0, 0.1);
                transform: translateY(-5px);
                box-shadow: 0 0 30px rgba(0, 255, 0, 0.3);
            }
            
            .feature-icon {
                font-size: 3em;
                margin-bottom: 15px;
            }
            
            .feature-title {
                font-size: 1.5em;
                color: #00ff00;
                margin-bottom: 10px;
                font-weight: bold;
            }
            
            .feature-desc {
                color: #00ff88;
                line-height: 1.6;
            }
            
            .endpoint-card {
                background: rgba(0, 255, 0, 0.05);
                border: 2px solid #00ff00;
                border-radius: 15px;
                padding: 25px;
                margin: 20px 0;
            }
            
            .method-badge {
                display: inline-block;
                padding: 8px 20px;
                border-radius: 25px;
                font-weight: bold;
                margin-right: 15px;
                font-size: 0.9em;
            }
            
            .method-get {
                background: linear-gradient(135deg, #00ff00, #00ff88);
                color: #000;
                box-shadow: 0 0 15px #00ff00;
            }
            
            .method-post {
                background: linear-gradient(135deg, #00ffff, #00ff88);
                color: #000;
                box-shadow: 0 0 15px #00ffff;
            }
            
            .code-block {
                background: #0a0a0a;
                border: 1px solid #00ff00;
                border-radius: 10px;
                padding: 20px;
                margin: 15px 0;
                overflow-x: auto;
                color: #00ff00;
                font-family: 'Courier New', monospace;
            }
            
            .live-stream {
                background: rgba(0, 255, 0, 0.05);
                border: 2px solid #00ff00;
                border-radius: 15px;
                padding: 25px;
                margin: 40px 0;
            }
            
            .stream-header {
                display: flex;
                align-items: center;
                margin-bottom: 20px;
            }
            
            .stream-indicator {
                width: 15px;
                height: 15px;
                background: #ff0000;
                border-radius: 50%;
                margin-right: 10px;
                animation: pulse 1s ease-in-out infinite;
            }
            
            .stream-title {
                font-size: 1.5em;
                color: #00ff00;
                font-weight: bold;
            }
            
            .stream-content {
                background: #0a0a0a;
                border: 1px solid #00ff00;
                border-radius: 10px;
                padding: 20px;
                min-height: 200px;
                max-height: 400px;
                overflow-y: auto;
                font-family: 'Courier New', monospace;
                color: #00ff88;
            }
            
            .stream-event {
                padding: 10px;
                margin: 5px 0;
                border-left: 3px solid #00ff00;
                padding-left: 15px;
                animation: fadeIn 0.5s;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateX(-20px); }
                to { opacity: 1; transform: translateX(0); }
            }
            
            .actions-table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            
            .actions-table th,
            .actions-table td {
                border: 1px solid #00ff00;
                padding: 15px;
                text-align: left;
            }
            
            .actions-table th {
                background: rgba(0, 255, 0, 0.2);
                color: #00ff00;
                font-weight: bold;
                text-shadow: 0 0 10px #00ff00;
            }
            
            .actions-table tr:hover {
                background: rgba(0, 255, 0, 0.1);
            }
            
            .footer {
                text-align: center;
                padding: 40px 20px;
                border-top: 2px solid #00ff00;
                margin-top: 60px;
                color: #00ff88;
            }
        </style>
    </head>
    <body>
        <div class="bg-animation"></div>
        
        <div class="container">
            <div class="header">
                <div class="logo">🔨</div>
                <h1 class="title">𝙃𝘼𝙈𝙈𝙀𝙍 𝘼𝙐𝙏𝙊𝙈𝘼𝙏𝙄𝙊𝙉 𝘼𝙄</h1>
                <p class="subtitle">⚡ 𝙋𝙧𝙤𝙛𝙚𝙨𝙨𝙞𝙤𝙣𝙖𝙡 𝘼𝙄-𝙋𝙤𝙬𝙚𝙧𝙚𝙙 𝘽𝙧𝙤𝙬𝙨𝙚𝙧 𝘼𝙪𝙩𝙤𝙢𝙖𝙩𝙞𝙤𝙣 𝙎𝙚𝙧𝙫𝙞𝙘𝙚 ⚡</p>
                <a href="https://t.me/developer_hammer" class="telegram-link" target="_blank">
                    📱 𝘾𝙤𝙣𝙩𝙖𝙘𝙩 𝙐𝙨 𝙤𝙣 𝙏𝙚𝙡𝙚𝙜𝙧𝙖𝙢
                </a>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">""" + str(len(active_sessions)) + """</div>
                    <div class="stat-label">🎯 𝘼𝙘𝙩𝙞𝙫𝙚 𝙎𝙚𝙨𝙨𝙞𝙤𝙣𝙨</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">""" + str(len(ai_sessions)) + """</div>
                    <div class="stat-label">🤖 𝘼𝙄 𝙎𝙚𝙨𝙨𝙞𝙤𝙣𝙨</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">v5.0.0</div>
                    <div class="stat-label">🚀 𝙑𝙚𝙧𝙨𝙞𝙤𝙣</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">✅</div>
                    <div class="stat-label">💚 𝙎𝙩𝙖𝙩𝙪𝙨</div>
                </div>
            </div>
            
            <div class="live-stream">
                <div class="stream-header">
                    <div class="stream-indicator"></div>
                    <div class="stream-title">📡 𝙇𝙞𝙫𝙚 𝘼𝙘𝙩𝙞𝙫𝙞𝙩𝙮 𝙎𝙩𝙧𝙚𝙖𝙢</div>
                </div>
                <div class="stream-content" id="liveStream">
                    <div class="stream-event">⏳ 𝙒𝙖𝙞𝙩𝙞𝙣𝙜 𝙛𝙤𝙧 𝙚𝙫𝙚𝙣𝙩𝙨...</div>
                </div>
            </div>
            
            <div class="features-section">
                <h2 class="section-title">✨ 𝙆𝙚𝙮 𝙁𝙚𝙖𝙩𝙪𝙧𝙚𝙨</h2>
                <div class="features-grid">
                    <div class="feature-card">
                        <div class="feature-icon">🤖</div>
                        <div class="feature-title">𝘼𝙄-𝙋𝙤𝙬𝙚𝙧𝙚𝙙 𝘼𝙪𝙩𝙤𝙢𝙖𝙩𝙞𝙤𝙣</div>
                        <div class="feature-desc">Advanced AI integration for intelligent browser control and decision making</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">🎭</div>
                        <div class="feature-title">𝙋𝙡𝙖𝙮𝙬𝙧𝙞𝙜𝙝𝙩 𝙋𝙤𝙬𝙚𝙧</div>
                        <div class="feature-desc">Full Playwright automation capabilities with stealth mode</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">📡</div>
                        <div class="feature-title">𝙇𝙞𝙫𝙚 𝙎𝙩𝙧𝙚𝙖𝙢𝙞𝙣𝙜</div>
                        <div class="feature-desc">Real-time activity monitoring and event streaming</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">🔒</div>
                        <div class="feature-title">𝙎𝙚𝙘𝙪𝙧𝙚 𝙎𝙚𝙨𝙨𝙞𝙤𝙣𝙨</div>
                        <div class="feature-desc">Multiple concurrent browser sessions with isolation</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">⚡</div>
                        <div class="feature-title">𝙃𝙞𝙜𝙝 𝙋𝙚𝙧𝙛𝙤𝙧𝙢𝙖𝙣𝙘𝙚</div>
                        <div class="feature-desc">Optimized for speed and reliability</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">📱</div>
                        <div class="feature-title">𝙏𝙚𝙡𝙚𝙜𝙧𝙖𝙢 𝘽𝙤𝙩</div>
                        <div class="feature-desc">Full control via Telegram with interactive buttons</div>
                    </div>
                </div>
            </div>
            
            <div class="features-section">
                <h2 class="section-title">🔧 𝘼𝙋𝙄 𝙀𝙣𝙙𝙥𝙤𝙞𝙣𝙩𝙨</h2>
                
                <div class="endpoint-card">
                    <h3>
                        <span class="method-badge method-get">GET</span>
                        <span style="color: #00ff00;">/api/health</span>
                    </h3>
                    <p style="color: #00ff88; margin: 15px 0;">💚 𝙃𝙚𝙖𝙡𝙩𝙝 𝙘𝙝𝙚𝙘𝙠 𝙚𝙣𝙙𝙥𝙤𝙞𝙣𝙩</p>
                    <div class="code-block">
{
  "status": "healthy",
  "browser_running": true,
  "active_sessions": 0,
  "ai_sessions": 0,
  "timestamp": "2025-11-08T07:00:00"
}
                    </div>
                </div>
                
                <div class="endpoint-card">
                    <h3>
                        <span class="method-badge method-post">POST</span>
                        <span style="color: #00ff00;">/api/automation</span>
                    </h3>
                    <p style="color: #00ff88; margin: 15px 0;">🎭 𝙈𝙖𝙞𝙣 𝙖𝙪𝙩𝙤𝙢𝙖𝙩𝙞𝙤𝙣 𝙚𝙣𝙙𝙥𝙤𝙞𝙣𝙩</p>
                    
                    <h4 style="color: #00ff00; margin: 20px 0;">📋 𝘼𝙫𝙖𝙞𝙡𝙖𝙗𝙡𝙚 𝘼𝙘𝙩𝙞𝙤𝙣𝙨:</h4>
                    <table class="actions-table">
                        <tr>
                            <th>🎯 𝘼𝙘𝙩𝙞𝙤𝙣</th>
                            <th>📝 𝘿𝙚𝙨𝙘𝙧𝙞𝙥𝙩𝙞𝙤𝙣</th>
                        </tr>
                        <tr>
                            <td>create</td>
                            <td>Create new browser session</td>
                        </tr>
                        <tr>
                            <td>navigate</td>
                            <td>Navigate to URL</td>
                        </tr>
                        <tr>
                            <td>click</td>
                            <td>Click element by selector</td>
                        </tr>
                        <tr>
                            <td>click_at</td>
                            <td>Click at coordinates (x, y)</td>
                        </tr>
                        <tr>
                            <td>hover_at</td>
                            <td>Hover at coordinates (x, y)</td>
                        </tr>
                        <tr>
                            <td>type</td>
                            <td>Type text in element</td>
                        </tr>
                        <tr>
                            <td>type_text_at</td>
                            <td>Type text at coordinates (x, y)</td>
                        </tr>
                        <tr>
                            <td>screenshot</td>
                            <td>Take screenshot</td>
                        </tr>
                        <tr>
                            <td>execute</td>
                            <td>Execute JavaScript</td>
                        </tr>
                        <tr>
                            <td>scroll_document</td>
                            <td>Scroll page (up, down, left, right)</td>
                        </tr>
                        <tr>
                            <td>scroll_at</td>
                            <td>Scroll at coordinates (x, y)</td>
                        </tr>
                        <tr>
                            <td>go_back</td>
                            <td>Go to previous page</td>
                        </tr>
                        <tr>
                            <td>go_forward</td>
                            <td>Go to next page</td>
                        </tr>
                        <tr>
                            <td>wait_5_seconds</td>
                            <td>Wait for 5 seconds</td>
                        </tr>
                        <tr>
                            <td>key_combination</td>
                            <td>Press keyboard keys</td>
                        </tr>
                        <tr>
                            <td>drag_and_drop</td>
                            <td>Drag and drop element</td>
                        </tr>
                        <tr>
                            <td>ai_command</td>
                            <td>Execute AI-powered command</td>
                        </tr>
                        <tr>
                            <td>get_content</td>
                            <td>Get page content</td>
                        </tr>
                        <tr>
                            <td>close</td>
                            <td>Close session</td>
                        </tr>
                    </table>
                </div>
            </div>
            
            <div class="footer">
                <p style="font-size: 1.5em; margin-bottom: 15px;">🔨 𝙃𝘼𝙈𝙈𝙀𝙍 𝘼𝙐𝙏𝙊𝙈𝘼𝙏𝙄𝙊𝙉 𝘼𝙄</p>
                <p>⚡ 𝙋𝙤𝙬𝙚𝙧𝙚𝙙 𝙗𝙮 𝘼𝙄 & 𝙋𝙡𝙖𝙮𝙬𝙧𝙞𝙜𝙝𝙩 ⚡</p>
                <p style="margin-top: 10px;">📱 <a href="https://t.me/developer_hammer" style="color: #00ff00; text-decoration: none;">@developer_hammer</a></p>
            </div>
        </div>
        
        <script>
            const streamContent = document.getElementById('liveStream');
            
            function addStreamEvent(message, type = 'info') {
                const event = document.createElement('div');
                event.className = 'stream-event';
                const timestamp = new Date().toLocaleTimeString();
                event.innerHTML = `[${timestamp}] ${message}`;
                streamContent.appendChild(event);
                streamContent.scrollTop = streamContent.scrollHeight;
                
                if (streamContent.children.length > 50) {
                    streamContent.removeChild(streamContent.firstChild);
                }
            }
            
            setInterval(() => {
                fetch('/api/health')
                    .then(r => r.json())
                    .then(data => {
                        if (data.last_activity) {
                            addStreamEvent(`💚 ${data.last_activity}`);
                        }
                    })
                    .catch(() => {});
            }, 5000);
            
            addStreamEvent('✅ 𝘾𝙤𝙣𝙣𝙚𝙘𝙩𝙚𝙙 𝙩𝙤 𝙡𝙞𝙫𝙚 𝙨𝙩𝙧𝙚𝙖𝙢');
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "emoji": "💚",
        "browser_running": browser is not None,
        "active_sessions": len(active_sessions),
        "ai_sessions": len(ai_sessions),
        "timestamp": datetime.now().isoformat(),
        "message": "✅ 𝙎𝙚𝙧𝙫𝙞𝙘𝙚 𝙞𝙨 𝙧𝙪𝙣𝙣𝙞𝙣𝙜 𝙨𝙢𝙤𝙤𝙩𝙝𝙡𝙮"
    }

@app.post("/api/automation")
async def automation_endpoint(request: AutomationRequest):
    try:
        action = request.action.lower()
        
        if action == "create":
            session_id = str(uuid.uuid4())
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            await inject_stealth_scripts(page)
            
            active_sessions[session_id] = {
                'context': context,
                'page': page,
                'created_at': datetime.now().isoformat()
            }
            
            await broadcast_event({
                "type": "session_created",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "action": "create",
                "session_id": session_id,
                "message": "✅ 𝙎𝙚𝙨𝙨𝙞𝙤𝙣 𝙘𝙧𝙚𝙖𝙩𝙚𝙙 𝙨𝙪𝙘𝙘𝙚𝙨𝙨𝙛𝙪𝙡𝙡𝙮"
            }
        
        if not request.session_id:
            raise HTTPException(status_code=400, detail="❌ session_id required")
        
        session = get_session(request.session_id)
        page = session['page']
        
        if action == "navigate":
            await page.goto(request.url, wait_until='networkidle', timeout=60000)
            title = await page.title()
            
            await broadcast_event({
                "type": "navigation",
                "url": request.url,
                "title": title,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "action": "navigate",
                "url": request.url,
                "title": title,
                "message": "✅ 𝙉𝙖𝙫𝙞𝙜𝙖𝙩𝙞𝙤𝙣 𝙨𝙪𝙘𝙘𝙚𝙨𝙨𝙛𝙪𝙡"
            }
        
        elif action == "click":
            await page.click(request.selector)
            await asyncio.sleep(request.wait_time / 1000)
            return {
                "success": True,
                "action": "click",
                "selector": request.selector,
                "message": "✅ 𝘾𝙡𝙞𝙘𝙠 𝙨𝙪𝙘𝙘𝙚𝙨𝙨𝙛𝙪𝙡"
            }
        
        elif action == "click_at":
            await page.mouse.click(request.x, request.y)
            await asyncio.sleep(request.wait_time / 1000)
            return {
                "success": True,
                "action": "click_at",
                "x": request.x,
                "y": request.y,
                "message": f"✅ 𝘾𝙡𝙞𝙘𝙠𝙚𝙙 𝙖𝙩 ({request.x}, {request.y})"
            }
        
        elif action == "hover_at":
            await page.mouse.move(request.x, request.y)
            return {
                "success": True,
                "action": "hover_at",
                "x": request.x,
                "y": request.y,
                "message": f"✅ 𝙃𝙤𝙫𝙚𝙧𝙚𝙙 𝙖𝙩 ({request.x}, {request.y})"
            }
        
        elif action == "type":
            await page.fill(request.selector, request.text)
            return {
                "success": True,
                "action": "type",
                "selector": request.selector,
                "message": "✅ 𝙏𝙚𝙭𝙩 𝙞𝙣𝙥𝙪𝙩 𝙨𝙪𝙘𝙘𝙚𝙨𝙨𝙛𝙪𝙡"
            }
        
        elif action == "type_text_at":
            await page.mouse.click(request.x, request.y)
            await page.keyboard.type(request.text)
            return {
                "success": True,
                "action": "type_text_at",
                "x": request.x,
                "y": request.y,
                "text": request.text,
                "message": f"✅ 𝙏𝙮𝙥𝙚𝙙 𝙩𝙚𝙭𝙩 𝙖𝙩 ({request.x}, {request.y})"
            }
        
        elif action == "screenshot":
            screenshot_bytes = await page.screenshot(full_page=request.full_page)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
            return {
                "success": True,
                "action": "screenshot",
                "screenshot": screenshot_b64,
                "message": "📸 𝙎𝙘𝙧𝙚𝙚𝙣𝙨𝙝𝙤𝙩 𝙘𝙖𝙥𝙩𝙪𝙧𝙚𝙙"
            }
        
        elif action == "execute":
            result = await page.evaluate(request.script)
            return {
                "success": True,
                "action": "execute",
                "result": result,
                "message": "⚙️ 𝙎𝙘𝙧𝙞𝙥𝙩 𝙚𝙭𝙚𝙘𝙪𝙩𝙚𝙙 𝙨𝙪𝙘𝙘𝙚𝙨𝙨𝙛𝙪𝙡𝙡𝙮"
            }
        
        elif action == "scroll_document":
            direction = request.direction or "down"
            if direction == "down":
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
            elif direction == "up":
                await page.evaluate("window.scrollBy(0, -window.innerHeight)")
            elif direction == "left":
                await page.evaluate("window.scrollBy(-window.innerWidth, 0)")
            elif direction == "right":
                await page.evaluate("window.scrollBy(window.innerWidth, 0)")
            
            return {
                "success": True,
                "action": "scroll_document",
                "direction": direction,
                "message": f"✅ 𝙎𝙘𝙧𝙤𝙡𝙡𝙚𝙙 {direction}"
            }
        
        elif action == "scroll_at":
            await page.mouse.move(request.x, request.y)
            await page.mouse.wheel(0, 100)
            return {
                "success": True,
                "action": "scroll_at",
                "x": request.x,
                "y": request.y,
                "message": f"✅ 𝙎𝙘𝙧𝙤𝙡𝙡𝙚𝙙 𝙖𝙩 ({request.x}, {request.y})"
            }
        
        elif action == "go_back":
            await page.go_back()
            return {
                "success": True,
                "action": "go_back",
                "message": "✅ 𝙒𝙚𝙣𝙩 𝙗𝙖𝙘𝙠"
            }
        
        elif action == "go_forward":
            await page.go_forward()
            return {
                "success": True,
                "action": "go_forward",
                "message": "✅ 𝙒𝙚𝙣𝙩 𝙛𝙤𝙧𝙬𝙖𝙧𝙙"
            }
        
        elif action == "wait_5_seconds":
            await asyncio.sleep(5)
            return {
                "success": True,
                "action": "wait_5_seconds",
                "message": "✅ 𝙒𝙖𝙞𝙩𝙚𝙙 5 𝙨𝙚𝙘𝙤𝙣𝙙𝙨"
            }
        
        elif action == "key_combination":
            keys = request.text.split('+')
            for key in keys:
                await page.keyboard.down(key.strip())
            for key in reversed(keys):
                await page.keyboard.up(key.strip())
            return {
                "success": True,
                "action": "key_combination",
                "keys": request.text,
                "message": f"✅ 𝙋𝙧𝙚𝙨𝙨𝙚𝙙 {request.text}"
            }
        
        elif action == "ai_command":
            if request.session_id not in ai_sessions:
                ai_session_id = await create_ai_session()
                if not ai_session_id:
                    raise HTTPException(status_code=500, detail="❌ Failed to create AI session")
                ai_sessions[request.session_id] = ai_session_id
            
            ai_session_id = ai_sessions[request.session_id]
            result = await execute_ai_command(ai_session_id, request.ai_prompt)
            
            return {
                "success": result["success"],
                "action": "ai_command",
                "prompt": request.ai_prompt,
                "thoughts": result.get("thoughts", []),
                "final_message": result.get("final_message", ""),
                "summary": result.get("summary", ""),
                "message": "🤖 𝘼𝙄 𝙘𝙤𝙢𝙢𝙖𝙣𝙙 𝙚𝙭𝙚𝙘𝙪𝙩𝙚𝙙"
            }
        
        elif action == "get_content":
            content = await page.content()
            url = page.url
            title = await page.title()
            return {
                "success": True,
                "action": "get_content",
                "content": content,
                "url": url,
                "title": title,
                "message": "📄 𝘾𝙤𝙣𝙩𝙚𝙣𝙩 𝙧𝙚𝙩𝙧𝙞𝙚𝙫𝙚𝙙 𝙨𝙪𝙘𝙘𝙚𝙨𝙨𝙛𝙪𝙡𝙡𝙮"
            }
        
        elif action == "close":
            await close_session_internal(request.session_id)
            if request.session_id in ai_sessions:
                del ai_sessions[request.session_id]
            
            await broadcast_event({
                "type": "session_closed",
                "session_id": request.session_id,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "action": "close",
                "session_id": request.session_id,
                "message": "✅ 𝙎𝙚𝙨𝙨𝙞𝙤𝙣 𝙘𝙡𝙤𝙨𝙚𝙙 𝙨𝙪𝙘𝙘𝙚𝙨𝙨𝙛𝙪𝙡𝙡𝙮"
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"❌ Unknown action: {action}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
