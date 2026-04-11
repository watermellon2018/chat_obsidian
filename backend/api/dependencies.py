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

# Populated by api/app.py lifespan before the first request arrives
_model: "BaseModel | None" = None
_config: "Config | None" = None
_mcp_client: "MCPClient | None" = None


def get_model() -> "BaseModel":
    assert _model is not None, "Model not initialised"
    return _model


def get_config() -> "Config":
    assert _config is not None, "Config not initialised"
    return _config


def get_mcp_client() -> "MCPClient":
    assert _mcp_client is not None, "MCPClient not initialised"
    return _mcp_client
