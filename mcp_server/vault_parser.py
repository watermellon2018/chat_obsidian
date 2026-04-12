from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


class VaultParser:
    """Reads, parses, and indexes markdown notes in an Obsidian vault."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path.resolve()
        self._backlink_index: dict[str, list[str]] | None = None

    # ------------------------------------------------------------------
    # File enumeration
    # ------------------------------------------------------------------

    def all_notes(self) -> list[dict]:
        """Return [{path, title, tags}] for every .md file (POSIX relative paths)."""
        results = []
        for md_file in sorted(self.vault_path.rglob("*.md")):
            rel = md_file.relative_to(self.vault_path).as_posix()
            content = self._read(md_file)
            meta = self.extract_metadata(content)
            title = self._extract_title(content, md_file.stem)
            results.append({"path": rel, "title": title, "tags": meta["tags"]})
        return results

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def read_note(self, rel_path: str) -> Optional[dict]:
        """Return {path, content, metadata} or None if file not found."""
        full = self.vault_path / rel_path
        if not full.exists():
            return None
        content = self._read(full)
        return {
            "path": rel_path,
            "content": content,
            "metadata": self.extract_metadata(content),
        }

    def _read(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Metadata / front-matter parsing
    # ------------------------------------------------------------------

    def extract_metadata(self, content: str) -> dict:
        meta: dict = {"tags": []}
        fm = self._get_front_matter(content)
        if not fm:
            return meta

        # Inline list:  tags: [python, mcp]
        inline = re.search(r"^tags:\s*\[([^\]]*)\]", fm, re.MULTILINE)
        if inline:
            meta["tags"] = [
                t.strip().lstrip("#")
                for t in inline.group(1).split(",")
                if t.strip()
            ]
            return meta

        # Block sequence:
        # tags:
        #   - python
        block = re.search(r"^tags:\s*\n((?:[ \t]+-[ \t]+\S+\n?)+)", fm, re.MULTILINE)
        if block:
            meta["tags"] = re.findall(r"[ \t]+-[ \t]+(\S+)", block.group(1))
        return meta

    def _get_front_matter(self, content: str) -> Optional[str]:
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        return m.group(1) if m else None

    def _extract_title(self, content: str, fallback: str) -> str:
        body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, count=1, flags=re.DOTALL)
        m = re.search(r"^#{1,6}\s+(.+)$", body, re.MULTILINE)
        return m.group(1).strip() if m else fallback

    # ------------------------------------------------------------------
    # Tag search
    # ------------------------------------------------------------------

    def notes_by_tag(self, tag: str) -> list[dict]:
        """Return notes that have the given tag (case-insensitive, # optional)."""
        tag_norm = tag.lstrip("#").lower()
        return [
            note
            for note in self.all_notes()
            if tag_norm in [t.lower() for t in note["tags"]]
        ]

    # ------------------------------------------------------------------
    # Backlinks
    # ------------------------------------------------------------------

    def build_backlink_index(self) -> dict[str, list[str]]:
        """Scan all notes for [[WikiLinks]] and build reverse index."""
        index: dict[str, list[str]] = {}
        for md_file in self.vault_path.rglob("*.md"):
            rel = md_file.relative_to(self.vault_path).as_posix()
            content = self._read(md_file)
            # Match [[Link]] or [[Link|Alias]] — capture only the link target
            links = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", content)
            for link in links:
                key = link.strip().lower()
                index.setdefault(key, [])
                if rel not in index[key]:
                    index[key].append(rel)
        return index

    def get_backlinks(self, note_name: str) -> list[dict]:
        """Return notes that [[link]] to *note_name* (stem match, case-insensitive)."""
        if self._backlink_index is None:
            self._backlink_index = self.build_backlink_index()

        key = Path(note_name).stem.lower()
        linking_paths = self._backlink_index.get(key, [])

        results = []
        for rel in linking_paths:
            full = self.vault_path / rel
            content = self._read(full)
            title = self._extract_title(content, Path(rel).stem)
            meta = self.extract_metadata(content)
            results.append({"path": rel, "title": title, "tags": meta["tags"]})
        return results