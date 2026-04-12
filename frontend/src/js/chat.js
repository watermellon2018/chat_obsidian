// chat.js — Alpine.data('chat') component factory

import { ChatWS } from './ws.js';
import { t, i18n } from './i18n.js';

/**
 * chatComponent — wraps the message list AND the input row.
 *
 * State shape:
 *   messages   — [{id, role:'user'|'bot'|'error', content, sources?}]
 *   pendingMsg — null | {showThinking:bool, tools:[{name,args,done,preview}]}
 *   inputText  — textarea value
 *   busy       — true while waiting for server response
 */
export function chatComponent() {
  return {
    messages:   [],
    pendingMsg: null,
    inputText:  '',
    busy:       false,
    _ws:        null,
    _nextId:    0,

    // ── Lifecycle ──────────────────────────────────────────────────────────

    init() {
      this._connectWS();

      // Reconnect when the user switches MCP ↔ RAG
      this.$watch(
        () => this.$store.app.chatMode,
        () => {
          if (this._ws) this._ws.close();
          this._connectWS();
        }
      );
    },

    destroy() {
      if (this._ws) this._ws.close();
    },

    // ── WebSocket ──────────────────────────────────────────────────────────

    _connectWS() {
      this._ws = new ChatWS({
        chatMode:    this.$store.app.chatMode,

        onOpen: () => {
          this.$store.app.wsConnected = true;
        },

        onClose: () => {
          this.$store.app.wsConnected = false;
          if (this.busy) {
            this.pendingMsg = null;
            this.busy = false;
          }
        },

        onToolStart: ({ tool, args }) => {
          if (this.pendingMsg) {
            this.pendingMsg.showThinking = false;
            this.pendingMsg.tools.push({ name: tool, args, done: false, preview: '' });
          }
          this._scrollBottom();
        },

        onToolEnd: ({ tool, preview }) => {
          if (this.pendingMsg) {
            const entry = this.pendingMsg.tools.find(tc => tc.name === tool && !tc.done);
            if (entry) { entry.done = true; entry.preview = preview; }
          }
        },

        onDone: ({ content, sources }) => {
          this.messages.push({
            id:      this._nextId++,
            role:    'bot',
            content,
            sources: sources || [],
          });
          this.pendingMsg = null;
          this.busy = false;
          this._scrollBottom();
        },

        onError: ({ content }) => {
          this.messages.push({ id: this._nextId++, role: 'error', content });
          this.pendingMsg = null;
          this.busy = false;
          this._scrollBottom();
        },
      });

      this._ws.connect();
    },

    // ── Send ───────────────────────────────────────────────────────────────

    send() {
      const text = this.inputText.trim();
      if (!text || this.busy || !this._ws?.isOpen) return;

      this.messages.push({ id: this._nextId++, role: 'user', content: text });
      this.pendingMsg = { showThinking: true, tools: [] };
      this.busy = true;
      this.inputText = '';

      this._ws.send(text, this.$store.app.lang);
      this._scrollBottom();
    },

    handleEnter(e) {
      if (!e.shiftKey) { e.preventDefault(); this.send(); }
    },

    // ── Helpers ────────────────────────────────────────────────────────────

    formatTool(name, args) {
      const lang = this.$store.app.lang;
      const map  = (i18n[lang] || i18n['en']).tools;
      return (map[name] || (() => `⚙ ${name}`))(args || {});
    },

    obsidianHref(src) {
      const vault = this.$store.app.vaultName;
      return vault
        ? `obsidian://open?vault=${encodeURIComponent(vault)}&file=${encodeURIComponent(src)}`
        : '#';
    },

    renderMarkdown(text) {
      return marked.parse(text || '');
    },

    _scrollBottom() {
      this.$nextTick(() => {
        const el = this.$refs.messageList;
        if (el) el.scrollTop = el.scrollHeight;
      });
    },
  };
}
