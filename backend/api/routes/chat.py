"""
Chat routes:
  WS  /ws               — MCP chat: model calls Obsidian tools
  WS  /ask              — RAG chat: answer based on FAISS search over chunks
  GET /flashcard/batch  — RAG flashcards: batch of 3-6 questions on one topic
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from api.dependencies import get_config, get_mcp_client, get_model, get_rag_chain
from services.orchestrator import Orchestrator
from services.rag import generate_flashcard_batch

log = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket) -> None:
    """One WebSocket connection = one independent MCP chat session."""
    await websocket.accept()

    model = get_model()
    mcp = get_mcp_client()
    config = get_config()
    orchestrator = Orchestrator(model, mcp, config)

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "").strip()
            if not message:
                continue
            async for event in orchestrator.handle_query_stream(message):
                await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "content": str(exc)})
        except Exception:
            pass


@router.websocket("/ask")
async def rag_ws(websocket: WebSocket) -> None:
    """
    RAG chat: each question → FAISS search → Gemini → answer.

    Message format matches /ws for frontend compatibility:
      Client → {"message": "question"}
      Server → {"type": "done", "content": "answer", "sources": [...]}
               {"type": "error", "content": "error text"}
    """
    await websocket.accept()

    rag = get_rag_chain()  # singleton — FAISS already loaded

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "").strip()
            if not message:
                continue

            try:
                result = await rag.ask(message)
                await websocket.send_json({
                    "type": "done",
                    "content": result.answer,
                    "sources": result.sources,
                })
            except Exception as exc:
                await websocket.send_json({"type": "error", "content": str(exc)})

    except WebSocketDisconnect:
        pass


@router.get("/flashcard/batch")
async def get_flashcard_batch(exclude_topics: str = "") -> dict:
    """
    Generates a batch of 3-6 flashcards on one topic from the knowledge base.

    Pipeline:
      1. Random chunk from FAISS
      2. Gemini extracts the key topic
      3. FAISS search by topic (top-5 chunks)
      4. Gemini generates 3-6 Q&A flashcards

    Query params:
      exclude_topics — comma-separated topics already shown to the user
                       (for deduplication between sessions)

    Returns:
      {"topic": "...", "cards": [{"question": ..., "answer": ..., "source": ...}, ...], "sources": [...]}
    """
    model = get_model()
    rag = get_rag_chain()  # raises HTTP 503 if FAISS not loaded

    exclude_list = [t.strip() for t in exclude_topics.split(",") if t.strip()]
    try:
        batch = await generate_flashcard_batch(
            model=model,
            retrieval=rag._retrieval,
            exclude_topics=exclude_list,
        )
    except Exception as exc:
        log.exception("generate_flashcard_batch failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return batch
