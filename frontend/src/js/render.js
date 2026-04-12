// render.js — Markdown (marked) + KaTeX (auto-render) for chat & flashcards

/** Delimiters: $$ display, $ inline; also \( \) / \[ \] for compatibility */
const KATEX_DELIMITERS = [
  { left: '$$', right: '$$', display: true },
  { left: '$', right: '$', display: false },
  { left: '\\(', right: '\\)', display: false },
  { left: '\\[', right: '\\]', display: true },
];

/**
 * Parse markdown into the given element, then run KaTeX on that subtree.
 * @param {HTMLElement} element
 * @param {string} markdown
 */
export function renderContent(element, markdown) {
  element.innerHTML = marked.parse(markdown || '');
  if (typeof window.renderMathInElement === 'function') {
    window.renderMathInElement(element, {
      delimiters: KATEX_DELIMITERS,
      throwOnError: false,
    });
  }
}

/**
 * For Alpine `x-html`: build HTML in a detached node (same pipeline as renderContent).
 * @param {string} markdown
 * @returns {string}
 */
export function renderMarkdownToHtml(markdown) {
  const wrap = document.createElement('div');
  renderContent(wrap, markdown);
  return wrap.innerHTML;
}
