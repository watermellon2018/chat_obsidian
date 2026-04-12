// api.js — Alpine global store factory

/**
 * appStore() — registered as Alpine.store('app').
 *
 * Reactive global state shared across all components:
 *   lang        — 'en' | 'ru', persisted in localStorage
 *   mode        — 'chat' | 'flashcards'
 *   chatMode    — 'mcp' | 'rag'
 *   vaultName   — fetched from /info on startup
 *   wsConnected — true when WebSocket is open
 */
export function appStore() {
  return {
    lang:        localStorage.getItem('lang') || 'en',
    mode:        'chat',
    chatMode:    'mcp',
    vaultName:   '',
    wsConnected: false,

    setLang(l) {
      this.lang = l;
      localStorage.setItem('lang', l);
      document.documentElement.lang = l;
    },

    setMode(m) {
      this.mode = m;
    },

    setChatMode(m) {
      this.chatMode = m;
    },

    async fetchVaultName() {
      try {
        const d = await fetch('/info').then(r => r.json());
        this.vaultName = d.vault_name || '';
      } catch {}
    },
  };
}
