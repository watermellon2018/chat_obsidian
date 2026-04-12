// ws.js — WebSocket wrapper with auto-reconnect

/**
 * ChatWS manages a single WebSocket connection.
 *
 * Options:
 *   chatMode    — 'mcp' | 'rag'  (determines endpoint)
 *   onOpen      — called when connection is established
 *   onClose     — called when connection drops (before reconnect attempt)
 *   onToolStart — called with { tool, args }
 *   onToolEnd   — called with { tool, preview }
 *   onDone      — called with { content, sources }
 *   onError     — called with { content }
 */
export class ChatWS {
  constructor({ chatMode, onOpen, onClose, onToolStart, onToolEnd, onDone, onError }) {
    this._chatMode   = chatMode;
    this._onOpen     = onOpen     || (() => {});
    this._onClose    = onClose    || (() => {});
    this._onToolStart = onToolStart || (() => {});
    this._onToolEnd  = onToolEnd  || (() => {});
    this._onDone     = onDone     || (() => {});
    this._onError    = onError    || (() => {});
    this._ws         = null;
  }

  connect() {
    const ws = new WebSocket(this._endpoint());
    this._ws = ws;

    ws.onopen = () => this._onOpen();

    ws.onclose = () => {
      this._onClose();
      // Reconnect after 2 s — only if onclose was not nulled by close()
      if (this._ws === ws) {
        setTimeout(() => this.connect(), 2000);
      }
    };

    ws.onmessage = e => {
      const ev = JSON.parse(e.data);
      switch (ev.type) {
        case 'tool_start': this._onToolStart({ tool: ev.tool, args: ev.args });        break;
        case 'tool_end':   this._onToolEnd({ tool: ev.tool, preview: ev.preview });    break;
        case 'done':       this._onDone({ content: ev.content, sources: ev.sources }); break;
        case 'error':      this._onError({ content: ev.content });                     break;
      }
    };
  }

  /**
   * Send a message.
   * @param {string} message
   * @param {string} lang — 'en' | 'ru'
   */
  send(message, lang) {
    if (this.isOpen) {
      this._ws.send(JSON.stringify({ message, language: lang }));
    }
  }

  /**
   * Deliberately close without triggering the reconnect loop.
   */
  close() {
    if (this._ws) {
      this._ws.onclose = null; // prevent reconnect
      this._ws.close();
      this._ws = null;
    }
  }

  get isOpen() {
    return this._ws?.readyState === WebSocket.OPEN;
  }

  _endpoint() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    return this._chatMode === 'rag'
      ? `${proto}://${location.host}/ask`
      : `${proto}://${location.host}/ws`;
  }
}
