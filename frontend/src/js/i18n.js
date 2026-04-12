// i18n.js — translation strings + stateless helpers

export const i18n = {
  en: {
    title:          'Obsidian MCP Chat',
    subtitle:       'Your notes are the primary source of truth',
    modeChat:       'Chat',
    modeFlash:      'Flashcards',
    placeholder:    'Ask about your notes… (Enter to send, Shift+Enter for newline)',
    sendBtn:        'Send',
    fcLabel:        'Question',
    fcGenerating:   'Generating…',
    fcTopicLoad:    'Loading topic…',
    fcProgressLoad: 'Loading…',
    fcPrev:         '← Previous',
    fcNext:         'Next card →',
    fcHint:         'Space — flip · ← / → navigate',
    fcTopic:        t => `🎯 ${t}`,
    topicLoading:   'Loading…',
    serverErr:      s => `Server error ${s}`,
    emptyBatch:     'Server returned an empty batch',
    tools: {
      search_notes:  a => `🔍 Search: ${a.query       || ''}`,
      read_note:     a => `📄 Reading: ${a.path        || ''}`,
      list_notes:    _  => '📋 List notes',
      search_by_tag: a => `🏷 Tag: ${a.tag            || ''}`,
      get_backlinks: a => `🔗 Backlinks: ${a.note_name || ''}`,
    },
  },
  ru: {
    title:          'Obsidian MCP Чат',
    subtitle:       'Ваши заметки — главный источник истины',
    modeChat:       'Чат',
    modeFlash:      'Карточки',
    placeholder:    'Спросите о ваших заметках… (Enter — отправить, Shift+Enter — перенос)',
    sendBtn:        'Отправить',
    fcLabel:        'Вопрос',
    fcGenerating:   'Генерация…',
    fcTopicLoad:    'Загрузка темы…',
    fcProgressLoad: 'Загрузка…',
    fcPrev:         '← Назад',
    fcNext:         'Следующая →',
    fcHint:         'Space — перевернуть · ← / → навигация',
    fcTopic:        t => `🎯 ${t}`,
    topicLoading:   'Загрузка…',
    serverErr:      s => `Ошибка сервера ${s}`,
    emptyBatch:     'Сервер вернул пустой батч',
    tools: {
      search_notes:  a => `🔍 Поиск: ${a.query       || ''}`,
      read_note:     a => `📄 Читаю: ${a.path         || ''}`,
      list_notes:    _  => '📋 Список заметок',
      search_by_tag: a => `🏷 Тег: ${a.tag            || ''}`,
      get_backlinks: a => `🔗 Ссылки: ${a.note_name   || ''}`,
    },
  },
};

/**
 * Stateless translation helper.
 * @param {string} lang  - 'en' | 'ru'
 * @param {string} key   - key from i18n object
 * @param {...any} args  - arguments forwarded to function-valued strings
 */
export function t(lang, key, ...args) {
  const val = i18n[lang]?.[key] ?? i18n['en'][key];
  return typeof val === 'function' ? val(...args) : (val ?? key);
}

/**
 * Alpine.data('appShell') — registered on <body>.
 * Exposes _t(key, ...args) so Alpine templates can call it without
 * passing lang explicitly.
 */
export function appShell() {
  return {
    _t(key, ...args) {
      return t(this.$store.app.lang, key, ...args);
    },
  };
}
