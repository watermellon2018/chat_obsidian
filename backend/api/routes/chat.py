"""
Chat routes:
  WS  /ws          — streaming chat per browser session
  GET /flashcard   — generate a Q&A flashcard from a random vault note
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.dependencies import get_config, get_mcp_client, get_model
from services.orchestrator import Orchestrator, generate_flashcard

router = APIRouter()


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket) -> None:
    """One WebSocket connection = one independent chat session."""
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


@router.get("/flashcard")
async def get_flashcard(exclude: str = "") -> dict:
    """
    Return a Q&A flashcard generated from a randomly chosen vault note.

    Query params:
      exclude — comma-separated list of note paths already shown to the user
    """
    model = get_model()
    mcp = get_mcp_client()
    config = get_config()

    exclude_list = [p for p in exclude.split(",") if p]
    card = await generate_flashcard(model, mcp, config, exclude_list)
    return card
