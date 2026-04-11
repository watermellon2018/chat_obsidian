"""
Retrieval service — placeholder for future RAG integration.

When adding RAG, implement this module and inject RetrievalService
into the Orchestrator via api/dependencies.py.

Suggested integration points
─────────────────────────────
1. Embed vault notes at startup (e.g. sentence-transformers or OpenAI embeddings)
   stored in a vector DB (e.g. ChromaDB, Qdrant, pgvector).

2. Replace the random note selection in services/orchestrator.py::generate_flashcard()
   with a semantic search call:

       relevant = await retrieval.search(query, top_k=3)

3. Add a /retrieval/search REST endpoint in api/routes/ for direct access.

4. Optionally feed RAG context into the Orchestrator's system prompt so the model
   always gets pre-retrieved context before calling MCP tools.

Example stub
─────────────

    from dataclasses import dataclass
    from pathlib import Path

    @dataclass
    class RetrievalResult:
        path: str
        content: str
        score: float

    class RetrievalService:
        def __init__(self, vault_path: Path) -> None:
            self.vault_path = vault_path
            # TODO: load vector index

        async def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
            # TODO: embed query and search vector index
            raise NotImplementedError("RAG not yet implemented")

        async def index(self) -> None:
            # TODO: embed all vault notes and store in vector DB
            raise NotImplementedError("RAG not yet implemented")
"""
