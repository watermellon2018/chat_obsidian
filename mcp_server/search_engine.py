from __future__ import annotations

import re
from pathlib import Path

from rank_bm25 import BM25Plus

from mcp_server.vault_parser import VaultParser


class SearchEngine:
    """BM25 full-text search over the vault. Index is built at startup."""

    def __init__(self, vault_parser: VaultParser) -> None:
        self._parser = vault_parser
        self._paths: list[str] = []
        self._titles: list[str] = []
        self._raw_contents: list[str] = []
        self._bm25: BM25Plus | None = None
        self._build()

    # ------------------------------------------------------------------
    # Index construction
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> list[str]:
        """Lowercase, strip markdown syntax noise, split on non-alphanumeric."""
        text = re.sub(r"[#*_`\[\]>~|]", " ", text.lower())
        return [tok for tok in re.split(r"\W+", text) if len(tok) > 1]

    def _build(self) -> None:
        notes = self._parser.all_notes()
        corpus: list[list[str]] = []
        for note in notes:
            data = self._parser.read_note(note["path"])
            content = data["content"] if data else ""
            self._paths.append(note["path"])
            self._titles.append(note["title"])
            self._raw_contents.append(content)
            corpus.append(self._tokenize(content))

        if corpus:
            self._bm25 = BM25Plus(corpus)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Return top-k results with path, title, snippet, score."""
        if not self._bm25 or not self._paths:
            return []

        tokens = self._tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in ranked[:limit]:
            if score <= 0:
                break
            snippet = self._extract_snippet(self._raw_contents[idx], tokens)
            results.append(
                {
                    "path": self._paths[idx],
                    "title": self._titles[idx],
                    "snippet": snippet,
                    "score": round(float(score), 4),
                }
            )
        return results

    def _extract_snippet(
        self, content: str, tokens: list[str], window: int = 200
    ) -> str:
        """Return a text window around the first query-token occurrence."""
        lower = content.lower()
        best_pos = len(content)
        for token in tokens:
            pos = lower.find(token)
            if 0 <= pos < best_pos:
                best_pos = pos

        start = max(0, best_pos - 60)
        end = min(len(content), best_pos + window)
        raw = content[start:end].replace("\n", " ").strip()
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(content) else ""
        return f"{prefix}{raw}{suffix}"
