"""
RAG chain — Tasks 3.2 and 3.3.

Contains two independent components:

  RagChain.ask()              — Task 3.2
    question → FAISS search → RAG_SYSTEM_PROMPT → model → coherent answer

  generate_rag_flashcard()    — Task 3.3
    random chunk from FAISS → RAG_FLASHCARD_PROMPT → model → JSON {question, answer}

Both components do NOT touch the MCP chain (orchestrator.py).
"""
from __future__ import annotations

import json
import random

from langchain_community.vectorstores import FAISS

from model.base import BaseModel
from prompts import (
    LANGUAGE_INSTRUCTION,
    RAG_BATCH_FLASHCARD_PROMPT,
    RAG_FLASHCARD_PROMPT,
    RAG_SYSTEM_PROMPT,
    RAG_TOPIC_EXTRACTION_PROMPT,
)
from retrieval.search import RetrievalService, SearchResult


class RagChain:
    """
    Chain: question → FAISS → prompt → model → answer.

    Created once at application startup:

        rag = RagChain(model=openrouter_model)

    Then called for each question:

        answer = await rag.ask("What is BM25?")
    """

    def __init__(self, model: BaseModel) -> None:
        self._model = model
        self._retrieval = RetrievalService()   # loads FAISS once

    # ------------------------------------------------------------------
    # Public method
    # ------------------------------------------------------------------

    async def ask(self, question: str, top_k: int = 8, language: str = "en") -> RagAnswer:
        """
        Accept a question, find relevant chunks, get an answer from the model.

        Parameters
        ----------
        question : user question
        top_k    : how many chunks to pass into context (default 3)
        language : "en" | "ru" — response language
        """
        # ── Step 1: semantic search via FAISS ─────────────────────────
        chunks: list[SearchResult] = self._retrieval.search(question, top_k=top_k)

        # ── Step 2: build the context text block ──────────────────────
        if chunks:
            context_block = _format_context(chunks)
        else:
            context_block = "No relevant fragments found in the knowledge base."

        # ── Step 3: inject context + language instruction into system prompt ──
        lang_note = LANGUAGE_INSTRUCTION.get(language, "")
        system_prompt = RAG_SYSTEM_PROMPT.format(context=context_block)
        if lang_note:
            system_prompt = f"{system_prompt}\n\n{lang_note}"

        # ── Step 4: call the model (without MCP tools) ────────────────
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": question},
        ]
        response = await self._model.chat(messages, tools=[])

        return RagAnswer(
            answer=response.text.strip(),
            sources=[c.source for c in chunks],
            chunks=chunks,
        )


# ------------------------------------------------------------------
# Helper types and functions
# ------------------------------------------------------------------

class RagAnswer:
    """Result of a single RAG call."""

    __slots__ = ("answer", "sources", "chunks")

    def __init__(
        self,
        answer: str,
        sources: list[str],
        chunks: list[SearchResult],
    ) -> None:
        self.answer = answer
        self.sources = sources    # unique note names
        self.chunks = chunks      # full objects for debugging

    def __repr__(self) -> str:
        return f"RagAnswer(sources={self.sources!r}, answer={self.answer[:60]!r}…)"


# ------------------------------------------------------------------
# Flashcard generator from FAISS — Task 3.3
# ------------------------------------------------------------------

async def generate_rag_flashcard(
    model: BaseModel,
    retrieval: RetrievalService,
    exclude: list[str] | None = None,
) -> dict:
    """
    Take a random chunk from FAISS and ask model to generate a flashcard.

    Difference from the old generate_flashcard() in orchestrator.py:
      - Old: a random full NOTE via MCP (list_notes → read_note)
      - This: a random CHUNK from FAISS (already split, ≤4000 characters)

    Parameters
    ----------
    model      : model (OpenRouter / Ollama)
    retrieval  : already loaded RetrievalService (FAISS in memory)
    exclude    : list of source names for already-shown flashcards (deduplication)

    Returns
    ----------
    {"question": "...", "answer": "...", "source": "<note name>"}
    """
    # ── Step 1: get all chunks from the FAISS index ───────────────────
    # LangChain stores documents in vector_store.docstore._dict: {id: Document}
    all_docs = list(retrieval._store.docstore._dict.values())

    if not all_docs:
        raise ValueError("FAISS index is empty — run vectorization.py first")

    # ── Step 2: exclude already-shown sources ─────────────────────────
    seen = set(exclude or [])
    candidates = [d for d in all_docs if d.metadata.get("source") not in seen]
    if not candidates:
        candidates = all_docs   # all shown → start over

    chunk = random.choice(candidates)
    source = chunk.metadata.get("source", "unknown")

    # ── Step 3: call the model with RAG_FLASHCARD_PROMPT ──────────────
    messages = [
        {"role": "system", "content": RAG_FLASHCARD_PROMPT},
        {"role": "user",   "content": chunk.page_content},
    ]
    response = await model.chat(messages, tools=[])
    raw_text = response.text.strip()

    # ── Step 4: parse JSON (strip markdown wrapper if model added one)
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    card: dict = json.loads(raw_text)
    card["source"] = source
    return card


# ------------------------------------------------------------------
# Flashcard batch generator — new pipeline
# ------------------------------------------------------------------

async def generate_flashcard_batch(
    model: BaseModel,
    retrieval: RetrievalService,
    exclude_topics: list[str] | None = None,
    top_k: int = 5,
    min_cards: int = 3,
    max_cards: int = 6,
    language: str = "en",
    topic: str | None = None,
) -> dict:
    """
    Generates a batch of 3-6 flashcards on one topic:

    1. Takes a random chunk from FAISS
    2. Asks model to extract the key topic (a short search query)
    3. Searches FAISS for top_k chunks on that topic
    4. Asks model to generate 3-6 flashcards from the found fragments
    5. Returns {"topic": "...", "cards": [...], "sources": [...]}

    Parameters
    ----------
    model          : language model
    retrieval      : loaded RetrievalService
    exclude_topics : list of topics already shown to the user (deduplication)
    top_k          : how many similar chunks to search by topic (default 5)
    min_cards      : minimum number of flashcards (passed to the prompt)
    max_cards      : maximum number of flashcards (passed to the prompt)
    """
    if topic:
        # ── User-specified topic: skip random chunk + LLM extraction ──
        pass
    else:
        # ── Step 1: random chunk from FAISS ───────────────────────────
        all_docs = list(retrieval._store.docstore._dict.values())
        if not all_docs:
            raise ValueError("FAISS index is empty — run vectorization.py first")

        seen = set(exclude_topics or [])
        candidates = [d for d in all_docs if d.metadata.get("source") not in seen]
        if not candidates:
            candidates = all_docs  # all topics shown → reset cycle

        seed_doc = random.choice(candidates)

        # ── Step 2: extract the key topic ─────────────────────────────
        topic_messages = [
            {"role": "system", "content": RAG_TOPIC_EXTRACTION_PROMPT},
            {"role": "user",   "content": seed_doc.page_content},
        ]
        topic_response = await model.chat(topic_messages, tools=[])
        topic = topic_response.text.strip().strip("\"'")

    # ── Step 3: search for similar chunks by topic ────────────────────
    chunks: list[SearchResult] = retrieval.search(topic, top_k=top_k)

    if not chunks:
        # Fallback: if search found nothing, use the seed document
        chunks = [
            SearchResult(
                content=seed_doc.page_content,
                source=seed_doc.metadata.get("source", "unknown"),
                score=1.0,
            )
        ]

    context_block = _format_context(chunks)

    # ── Step 4: generate the flashcard batch ──────────────────────────
    lang_note = LANGUAGE_INSTRUCTION.get(language, "")
    user_topic_note = f"\nUser-specified topic: {topic}" if topic else ""
    cards_system = (
        f"{RAG_BATCH_FLASHCARD_PROMPT}{user_topic_note}\n\n{lang_note}" if lang_note
        else f"{RAG_BATCH_FLASHCARD_PROMPT}{user_topic_note}"
    )
    cards_messages = [
        {"role": "system", "content": cards_system},
        {
            "role": "user",
            "content": (
                f"Topic: {topic}\n\n"
                f"Generate {min_cards} to {max_cards} flashcards "
                f"based on the following fragments:\n\n{context_block}"
            ),
        },
    ]
    cards_response = await model.chat(cards_messages, tools=[])
    raw_text = cards_response.text.strip()

    # Strip markdown wrapper if the model added one anyway
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    cards: list[dict] = json.loads(raw_text)

    return {
        "topic": topic,
        "cards": cards,
        "sources": list({c.source for c in chunks}),
    }


# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------

def _format_context(chunks: list[SearchResult]) -> str:
    """
    Convert a list of SearchResult into a text block for the prompt.

    Format of each fragment:
        [Note: <name>] (relevance: 0.87)
        <chunk text>
    """
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(
            f"[Note: {chunk.source}] (relevance: {chunk.score})\n{chunk.content}"
        )
    return "\n\n---\n\n".join(parts)
