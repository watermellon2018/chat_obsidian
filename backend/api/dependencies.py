"""
FastAPI dependency providers.

The model, config, and shared MCP client are created once at startup
(in api/app.py lifespan) and stored as module-level singletons here.
Route handlers import them via Depends() or directly.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from client.mcp_client import MCPClient
    from config import Config
    from model.base import BaseModel
    from services.rag import RagChain

# Populated by api/app.py lifespan before the first request arrives
_model: "BaseModel | None" = None
_config: "Config | None" = None
_mcp_client: "MCPClient | None" = None
_rag_chain: "RagChain | None" = None


def get_model() -> "BaseModel":
    assert _model is not None, "Model not initialised"
    return _model


def get_config() -> "Config":
    assert _config is not None, "Config not initialised"
    return _config


def get_mcp_client() -> "MCPClient":
    assert _mcp_client is not None, "MCPClient not initialised"
    return _mcp_client


def get_rag_chain() -> "RagChain":
    """
    Returns the shared RagChain singleton (loads FAISS once at startup).
    Raises HTTP 503 if FAISS index was not loaded (index not built yet).
    """
    if _rag_chain is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=(
                "FAISS index is not available. "
                "Run vectorization.py to build it first, "
                "then set SAVE_INDEX_PATH in your .env file."
            ),
        )
    return _rag_chain
