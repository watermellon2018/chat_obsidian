from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

load_dotenv()


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    """A single text fragment found in the database."""
    content: str    # chunk text (with the note title)
    source: str     # note name (from metadata["source"])
    score: float    # relevance 0..1, higher is better


# ---------------------------------------------------------------------------
# Database loading
# ---------------------------------------------------------------------------

def load_faiss() -> FAISS:
    """
    Loads the FAISS index from disk.
    The path is taken from the SAVE_INDEX_PATH environment variable.
    """
    index_path = os.getenv("SAVE_INDEX_PATH")
    if not index_path:
        raise EnvironmentError("Set SAVE_INDEX_PATH in the .env file")

    print("Loading FAISS index...")

    embeddings = OpenAIEmbeddings(
        model="openai/text-embedding-3-small",
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
    )

    vector_store = FAISS.load_local(
        index_path,
        embeddings,
        allow_dangerous_deserialization=True,
    )

    print("FAISS index loaded.")
    return vector_store


# ---------------------------------------------------------------------------
# Search function (Task 2.2)
# ---------------------------------------------------------------------------

def search(query: str, vector_store: FAISS, top_k: int = 3) -> list[SearchResult]:
    """
    Accepts a query string, converts it to a vector and returns
    the top_k most similar fragments from the database.

    Parameters
    ----------
    query        : question or key phrase to search for
    vector_store : loaded FAISS index (result of load_faiss())
    top_k        : how many results to return (default 3)

    Returns
    ----------
    List of SearchResult sorted from most to least relevant.
    Score is normalised to the range [0, 1]; 1.0 is a perfect match.
    """
    if not query.strip():
        return []

    # similarity_search_with_relevance_scores returns [(Document, float), ...]
    # float — cosine similarity normalised to [0, 1]
    docs_and_scores = vector_store.similarity_search_with_relevance_scores(
        query, k=top_k
    )

    results: list[SearchResult] = []
    for doc, score in docs_and_scores:
        results.append(
            SearchResult(
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown note"),
                score=round(score, 4),
            )
        )

    return results


# ---------------------------------------------------------------------------
# RetrievalService — a convenient wrapper for use in the API
# ---------------------------------------------------------------------------

class RetrievalService:
    """
    Encapsulates the FAISS index and the search method.
    Created once at application startup (in lifespan).

    Example usage:
        retrieval = RetrievalService()
        results = retrieval.search("What is BM25?")
        for r in results:
            print(r.score, r.source, r.content[:80])
    """

    def __init__(self) -> None:
        self._store: FAISS = load_faiss()

    def search(self, query: str, top_k: int = 3) -> list[SearchResult]:
        """
        Find the top_k most similar fragments by query string.

        RAG hook: this method will be called from services/orchestrator.py
        to pass context to the model before answering the user.
        """
        return search(query, self._store, top_k=top_k)