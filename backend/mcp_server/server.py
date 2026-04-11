"""
MCP server for the Obsidian vault.

Runs as a subprocess via stdio transport.
The client spawns this process and communicates over stdin/stdout using
the MCP JSON-RPC 2.0 protocol.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add backend/ to sys.path so that `mcp_server.*` imports resolve correctly
# when this script is run as a subprocess from any working directory.
_backend_root = Path(__file__).parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

from mcp_server.vault_parser import VaultParser
from mcp_server.search_engine import SearchEngine

# ------------------------------------------------------------------
# Initialization (runs once when the subprocess starts)
# ------------------------------------------------------------------

VAULT_PATH = Path(os.getenv("VAULT_PATH", "./vault")).resolve()

_parser = VaultParser(VAULT_PATH)
_search = SearchEngine(_parser)

mcp = FastMCP("obsidian-vault")

# ------------------------------------------------------------------
# Tool definitions
# ------------------------------------------------------------------


@mcp.tool()
def list_notes() -> list[dict]:
    """
    List all notes in the Obsidian vault.
    Returns a list of objects, each with 'path' (relative), 'title', and 'tags'.
    Use this to discover what notes exist before searching.
    """
    return _parser.all_notes()


@mcp.tool()
def search_notes(query: str, limit: int = 5) -> list[dict]:
    """
    Search the vault using BM25 full-text search (no embeddings).
    Returns a list of objects with 'path', 'title', 'snippet', and 'score'.
    Call this tool FIRST for any user query about vault content.
    Higher score = more relevant.
    """
    return _search.search(query, limit=limit)


@mcp.tool()
def read_note(path: str) -> dict:
    """
    Read the full markdown content of a note by its relative path.
    Returns an object with 'path', 'content' (full markdown), and 'metadata' (tags etc.).
    Use the 'path' value returned by search_notes or list_notes.
    Returns {'error': '...'} if the note is not found.
    """
    result = _parser.read_note(path)
    if result is None:
        return {"error": f"Note not found: {path}"}
    return result


@mcp.tool()
def search_by_tag(tag: str) -> list[dict]:
    """
    Find all notes that have a specific tag.
    The '#' prefix is optional and the match is case-insensitive.
    Returns a list of objects with 'path', 'title', and 'tags'.
    """
    return _parser.notes_by_tag(tag)


@mcp.tool()
def get_backlinks(note_name: str) -> list[dict]:
    """
    Find all notes that contain a [[WikiLink]] pointing to the given note.
    'note_name' can be just the stem (e.g. 'Python_Best_Practices') or include '.md'.
    Returns a list of objects with 'path', 'title', and 'tags'.
    """
    return _parser.get_backlinks(note_name)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()  # stdio transport — reads from stdin, writes to stdout
