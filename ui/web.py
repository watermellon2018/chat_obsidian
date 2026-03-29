"""
FastAPI web interface for Obsidian MCP Chat.

Routes:
  GET /    → chat HTML page (served inline)
  WS  /ws  → WebSocket per browser session

WebSocket message protocol:
  Client → Server:  {"message": "user text"}
  Server → Client:
    {"type": "tool_start", "tool": "search_notes", "args": {...}}
    {"type": "tool_end",   "tool": "search_notes", "preview": "..."}
    {"type": "done",       "content": "final answer"}
    {"type": "error",      "content": "error text"}
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

if TYPE_CHECKING:
    from config import Config
    from model.base import BaseModel

# ---------------------------------------------------------------------------
# Module-level state injected by run.py before uvicorn starts
# ---------------------------------------------------------------------------
_model: "BaseModel | None" = None
_config: "Config | None" = None

# ---------------------------------------------------------------------------
# Shared MCP client — initialized in lifespan so it lives in the main task
# ---------------------------------------------------------------------------
_mcp_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start MCP server subprocess at app startup; shut it down on exit."""
    global _mcp_client
    from client.mcp_client import MCPClient
    _mcp_client = MCPClient()
    await _mcp_client.__aenter__()
    yield
    await _mcp_client.__aexit__(None, None, None)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Obsidian MCP Chat", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(_HTML)


@app.websocket("/ws")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
    from client.orchestrator import Orchestrator

    orchestrator = Orchestrator(_model, _mcp_client, _config)

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "").strip()
            if not message:
                continue
            async for event in orchestrator.handle_query_stream(message):
                await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "content": str(exc)})
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Inline HTML / CSS / JS  (no external files needed)
# ---------------------------------------------------------------------------
_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Obsidian MCP Chat</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:       #1e1e2e;
    --surface:  #2a2a3e;
    --border:   #3a3a52;
    --text:     #cdd6f4;
    --muted:    #7f849c;
    --accent:   #89b4fa;
    --user-bg:  #313244;
    --bot-bg:   #252535;
    --tool-bg:  #1e3a4c;
    --tool-txt: #74c7ec;
    --err-bg:   #3c1f24;
    --err-txt:  #f38ba8;
    --radius:   12px;
    --font:     'Segoe UI', system-ui, sans-serif;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    height: 100dvh;
    display: flex;
    flex-direction: column;
  }

  /* ── Header ── */
  header {
    padding: 14px 20px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }
  header h1 { font-size: 1rem; font-weight: 600; color: var(--accent); }
  header span { font-size: .8rem; color: var(--muted); }
  .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #a6e3a1; flex-shrink: 0;
  }
  .dot.offline { background: var(--muted); }

  /* ── Chat area ── */
  #chat {
    flex: 1;
    overflow-y: auto;
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    scroll-behavior: smooth;
  }

  /* ── Messages ── */
  .msg {
    display: flex;
    flex-direction: column;
    max-width: 78%;
    animation: fadeIn .2s ease;
  }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } }

  .msg.user  { align-self: flex-end; align-items: flex-end; }
  .msg.bot   { align-self: flex-start; align-items: flex-start; }

  .bubble {
    padding: 10px 14px;
    border-radius: var(--radius);
    line-height: 1.6;
    font-size: .92rem;
    word-break: break-word;
  }
  .msg.user .bubble {
    background: var(--user-bg);
    border-bottom-right-radius: 3px;
  }
  .msg.bot .bubble {
    background: var(--bot-bg);
    border: 1px solid var(--border);
    border-bottom-left-radius: 3px;
  }
  .msg.error .bubble {
    background: var(--err-bg);
    color: var(--err-txt);
    border: 1px solid var(--err-txt);
  }

  /* Markdown inside bubbles */
  .bubble h1,.bubble h2,.bubble h3 { margin: .6em 0 .3em; color: var(--accent); }
  .bubble p  { margin: .3em 0; }
  .bubble ul,.bubble ol { padding-left: 1.4em; margin: .3em 0; }
  .bubble code {
    background: rgba(255,255,255,.07);
    padding: 1px 5px; border-radius: 4px;
    font-size: .85em; font-family: monospace;
  }
  .bubble pre {
    background: rgba(255,255,255,.05);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 12px;
    overflow-x: auto;
    margin: .5em 0;
  }
  .bubble pre code { background: none; padding: 0; }
  .bubble strong { color: var(--accent); }
  .bubble blockquote {
    border-left: 3px solid var(--accent);
    padding-left: 10px;
    color: var(--muted);
    margin: .3em 0;
  }

  /* ── Tool activity chips ── */
  .tool-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: .78rem;
    color: var(--tool-txt);
    background: var(--tool-bg);
    border: 1px solid var(--tool-txt);
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 4px;
    animation: fadeIn .15s ease;
  }
  .tool-chip .spinner {
    width: 10px; height: 10px;
    border: 2px solid transparent;
    border-top-color: var(--tool-txt);
    border-radius: 50%;
    animation: spin .7s linear infinite;
    flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .tool-chip.done .spinner { display: none; }
  .tool-chip.done::before { content: '✓'; font-size: .75rem; }

  /* ── Thinking indicator ── */
  .thinking {
    display: flex; gap: 4px; align-items: center;
    padding: 10px 14px;
    background: var(--bot-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    border-bottom-left-radius: 3px;
  }
  .thinking span {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--muted);
    animation: bounce .9s infinite;
  }
  .thinking span:nth-child(2) { animation-delay: .15s; }
  .thinking span:nth-child(3) { animation-delay: .30s; }
  @keyframes bounce {
    0%,60%,100% { transform: translateY(0); }
    30%          { transform: translateY(-5px); }
  }

  /* ── Input row ── */
  #input-row {
    padding: 12px 16px;
    background: var(--surface);
    border-top: 1px solid var(--border);
    display: flex;
    gap: 8px;
    align-items: flex-end;
    flex-shrink: 0;
  }
  #msg {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-family: var(--font);
    font-size: .92rem;
    padding: 10px 14px;
    resize: none;
    max-height: 140px;
    outline: none;
    transition: border-color .2s;
    overflow-y: auto;
  }
  #msg:focus { border-color: var(--accent); }
  #msg::placeholder { color: var(--muted); }

  #send {
    background: var(--accent);
    color: var(--bg);
    border: none;
    border-radius: var(--radius);
    padding: 10px 18px;
    font-size: .9rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity .2s;
    flex-shrink: 0;
    height: 40px;
  }
  #send:hover  { opacity: .85; }
  #send:disabled { opacity: .4; cursor: default; }
</style>
</head>
<body>

<header>
  <div class="dot" id="dot"></div>
  <h1>Obsidian MCP Chat</h1>
  <span>Your notes are the primary source of truth</span>
</header>

<div id="chat"></div>

<div id="input-row">
  <textarea id="msg" rows="1" placeholder="Ask about your notes… (Enter to send, Shift+Enter for newline)"></textarea>
  <button id="send">Send</button>
</div>

<script>
  marked.setOptions({ breaks: true, gfm: true });

  const chat    = document.getElementById('chat');
  const msgEl   = document.getElementById('msg');
  const sendBtn = document.getElementById('send');
  const dot     = document.getElementById('dot');

  let ws = null;
  let botMsg = null;      // current bot message element being built
  let toolsEl = null;     // container for tool chips above bot message
  let thinking = null;    // thinking indicator element
  let busy = false;

  // ── WebSocket ──────────────────────────────────────────────────────────
  function connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws`);

    ws.onopen = () => {
      dot.classList.remove('offline');
    };

    ws.onclose = () => {
      dot.classList.add('offline');
      setBusy(false);
      setTimeout(connect, 2000);
    };

    ws.onmessage = (e) => {
      const ev = JSON.parse(e.data);

      if (ev.type === 'tool_start') {
        removeThinking();
        const chip = makeToolChip(ev.tool, ev.args, false);
        if (!toolsEl) {
          toolsEl = document.createElement('div');
          toolsEl.className = 'msg bot';
          chat.appendChild(toolsEl);
        }
        chip.dataset.tool = ev.tool;
        toolsEl.appendChild(chip);
        scrollBottom();

      } else if (ev.type === 'tool_end') {
        // Mark matching chip as done
        if (toolsEl) {
          const chip = toolsEl.querySelector(`[data-tool="${ev.tool}"]:not(.done)`);
          if (chip) chip.classList.add('done');
        }

      } else if (ev.type === 'done') {
        removeThinking();
        toolsEl = null;
        appendBot(ev.content);
        setBusy(false);

      } else if (ev.type === 'error') {
        removeThinking();
        toolsEl = null;
        appendError(ev.content);
        setBusy(false);
      }
    };
  }

  // ── Message helpers ────────────────────────────────────────────────────
  function appendUser(text) {
    const el = document.createElement('div');
    el.className = 'msg user';
    el.innerHTML = `<div class="bubble">${escHtml(text)}</div>`;
    chat.appendChild(el);
    scrollBottom();
  }

  function appendBot(markdown) {
    const el = document.createElement('div');
    el.className = 'msg bot';
    el.innerHTML = `<div class="bubble">${marked.parse(markdown)}</div>`;
    chat.appendChild(el);
    scrollBottom();
  }

  function appendError(text) {
    const el = document.createElement('div');
    el.className = 'msg error';
    el.innerHTML = `<div class="bubble">⚠ ${escHtml(text)}</div>`;
    chat.appendChild(el);
    scrollBottom();
  }

  function showThinking() {
    thinking = document.createElement('div');
    thinking.className = 'msg bot';
    thinking.innerHTML = '<div class="thinking"><span></span><span></span><span></span></div>';
    chat.appendChild(thinking);
    scrollBottom();
  }

  function removeThinking() {
    if (thinking) { thinking.remove(); thinking = null; }
  }

  function makeToolChip(tool, args, done) {
    const chip = document.createElement('div');
    chip.className = 'tool-chip' + (done ? ' done' : '');
    const label = formatTool(tool, args);
    chip.innerHTML = `<span class="spinner"></span>${escHtml(label)}`;
    return chip;
  }

  function formatTool(tool, args) {
    const map = {
      search_notes:  a => `🔍 Searching: ${a.query || ''}`,
      read_note:     a => `📄 Reading: ${a.path || ''}`,
      list_notes:    _  => '📋 Listing notes',
      search_by_tag: a => `🏷 Tag: ${a.tag || ''}`,
      get_backlinks: a => `🔗 Backlinks: ${a.note_name || ''}`,
    };
    return (map[tool] || (() => `⚙ ${tool}`))(args || {});
  }

  function escHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function scrollBottom() {
    requestAnimationFrame(() => { chat.scrollTop = chat.scrollHeight; });
  }

  // ── Send ───────────────────────────────────────────────────────────────
  function setBusy(val) {
    busy = val;
    sendBtn.disabled = val;
    msgEl.disabled   = val;
  }

  function send() {
    const text = msgEl.value.trim();
    if (!text || busy || !ws || ws.readyState !== WebSocket.OPEN) return;

    appendUser(text);
    showThinking();
    setBusy(true);
    ws.send(JSON.stringify({ message: text }));
    msgEl.value = '';
    msgEl.style.height = 'auto';
  }

  sendBtn.addEventListener('click', send);

  msgEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });

  // Auto-resize textarea
  msgEl.addEventListener('input', () => {
    msgEl.style.height = 'auto';
    msgEl.style.height = Math.min(msgEl.scrollHeight, 140) + 'px';
  });

  connect();
</script>
</body>
</html>"""
