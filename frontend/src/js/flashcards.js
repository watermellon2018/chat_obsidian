// flashcards.js — Alpine.data('flashcards') component factory

import { t } from './i18n.js';

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
      // Auto-fetch when switching to flashcards mode for the first time
      this.$watch(
        () => this.$store.app.mode,
        m => {
          if (m === 'flashcards' && !this.currentBatch.length) this.fetchBatch();
        }
      );
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
      if (e.key === ' ')                            { e.preventDefault(); this.flipCard(); }
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

    // ── Fetch ──────────────────────────────────────────────────────────────

    async fetchBatch() {
      this.loading     = true;
      this.error       = null;
      this.cardFlipped = false;
      this.topic       = '';

      const lang    = this.$store.app.lang;
      const exclude = this.seenTopics.join(',');

      try {
        const res = await fetch(
          `/flashcard/batch?exclude_topics=${encodeURIComponent(exclude)}&lang=${lang}`
        );
        if (!res.ok) throw new Error(t(lang, 'serverErr', res.status));

        const data = await res.json();
        const cards = data.cards || [];
        if (!cards.length) throw new Error(t(lang, 'emptyBatch'));

        this.currentBatch = cards;
        this.batchIndex   = 0;
        this.topic        = data.topic || '';
        this.seenTopics.push(data.topic);
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },
  };
}
