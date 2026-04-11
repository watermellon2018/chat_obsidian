"""
FastAPI application factory.

The app is created once and shared by all routes.
The lifespan context manager owns the MCP server subprocess — this must
live in the main asyncio task to avoid anyio cancel-scope errors.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

if TYPE_CHECKING:
    from config import Config
    from model.base import BaseModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start MCP server subprocess at startup; shut it down cleanly on exit."""
    import api.dependencies as deps
    from client.mcp_client import MCPClient

    deps._mcp_client = MCPClient()
    await deps._mcp_client.__aenter__()
    try:
        yield
    finally:
        await deps._mcp_client.__aexit__(None, None, None)


def create_app(model: "BaseModel", config: "Config") -> FastAPI:
    """
    Build and return the configured FastAPI application.

    Called by main.py after the model and config are constructed.
    """
    import api.dependencies as deps
    from api.routes.chat import router as chat_router
    from api.routes.health import router as health_router

    # Inject singletons before the first request
    deps._model = model
    deps._config = config

    app = FastAPI(
        title="Obsidian MCP Backend",
        description="Knowledge-first assistant backed by an Obsidian vault.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(chat_router)
    app.include_router(health_router)

    return app
