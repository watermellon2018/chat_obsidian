// flashcards.js — Alpine.data('flashcards') component factory

import { t } from './i18n.js';
import { renderMarkdownToHtml } from './render.js';

/**
 * flashcardsComponent — manages batch fetching, card navigation, and flip.
 *
 * State shape:
 *   currentBatch — array of {question, answer, source} from /flashcard/batch
 *   batchIndex   — index of the currently shown card
 *   cardFlipped  — whether the card is showing the answer side
 *   seenTopics   — list of topics already shown (for deduplication)
 *   topic        — current batch topic string
 *   loading      — true while fetching a new batch
 *   error        — error message string or null
 */
export function flashcardsComponent() {
  return {
    currentBatch: [],
    batchIndex:   0,
    cardFlipped:  false,
    seenTopics:   [],
    topic:        '',
    userTopic:    '',
    loading:      false,
    error:        null,

    // ── Computed getters ───────────────────────────────────────────────────

    get currentCard() {
      return this.currentBatch[this.batchIndex] || null;
    },

    get progress() {
      if (!this.currentBatch.length) return '';
      return `${this.batchIndex + 1} / ${this.currentBatch.length}`;
    },

    get topicLabel() {
      if (!this.topic) return '';
      return t(this.$store.app.lang, 'fcTopic', this.topic);
    },

    get isPrevDisabled() {
      return this.loading || this.batchIndex === 0;
    },

    get isNextDisabled() {
      return this.loading;
    },

    // ── Lifecycle ──────────────────────────────────────────────────────────

    init() {
      // No auto-fetch: user must click Generate or Random explicitly
    },

    // ── Navigation ─────────────────────────────────────────────────────────

    prevCard() {
      if (this.batchIndex > 0) {
        this.batchIndex--;
        this.cardFlipped = false;
      }
    },

    nextCard() {
      if (!this.currentBatch.length) {
        this.fetchBatch();
        return;
      }
      const next = this.batchIndex + 1;
      if (next < this.currentBatch.length) {
        this.batchIndex  = next;
        this.cardFlipped = false;
      } else {
        // Last card — fetch next batch
        this.currentBatch = [];
        this.batchIndex   = 0;
        this.fetchBatch();
      }
    },

    flipCard() {
      this.cardFlipped = !this.cardFlipped;
    },

    // ── Keyboard handler (bound via @keydown.window) ────────────────────────

    handleKey(e) {
      if (this.$store.app.mode !== 'flashcards') return;
      // Don't intercept keystrokes while user is typing in an input or textarea
      const tag = document.activeElement?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (e.key === ' ')                                { e.preventDefault(); this.flipCard(); }
      else if (e.key === 'ArrowRight' || e.key === 'n') { e.preventDefault(); this.nextCard(); }
      else if (e.key === 'ArrowLeft'  || e.key === 'p') { e.preventDefault(); this.prevCard(); }
    },

    // ── Obsidian deep link ─────────────────────────────────────────────────

    obsidianHref(src) {
      const vault = this.$store.app.vaultName;
      return vault
        ? `obsidian://open?vault=${encodeURIComponent(vault)}&file=${encodeURIComponent(src)}`
        : '#';
    },

    /** Markdown + KaTeX for card face (Alpine x-html). */
    renderCardMarkdown(field) {
      const c = this.currentCard;
      if (!c) return '';
      const raw = field === 'question' ? c.question : c.answer;
      return renderMarkdownToHtml(raw || '');
    },

    // ── Fetch ─────────────────────────────────────────────────────────────

    /** Generate with userTopic cleared — pure random mode. */
    async fetchRandom() {
      this.userTopic = '';
      await this.fetchBatch();
    },

    async fetchBatch() {
      this.loading     = true;
      this.error       = null;
      this.cardFlipped = false;
      this.topic       = '';

      const lang       = this.$store.app.lang;
      const exclude    = this.seenTopics.join(',');
      const trimmed    = this.userTopic.trim();
      const topicParam = trimmed ? `&topic=${encodeURIComponent(trimmed)}` : '';

      try {
        const res = await fetch(
          `/flashcard/batch?exclude_topics=${encodeURIComponent(exclude)}&lang=${lang}${topicParam}`
        );
        if (!res.ok) throw new Error(t(lang, 'serverErr', res.status));

        const data = await res.json();
        const cards = data.cards || [];
        if (!cards.length) throw new Error(t(lang, 'emptyBatch'));

        this.currentBatch = cards;
        this.batchIndex   = 0;
        this.topic        = data.topic || '';
        // Не дедуплицируем если тема задана вручную
        if (!trimmed) this.seenTopics.push(data.topic);
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },
  };
}
