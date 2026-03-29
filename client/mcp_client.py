"""
MCP client that spawns the vault server as a subprocess and communicates
over stdio using the official MCP Python SDK.
"""
from __future__ import annotations

import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """
    Async context manager that manages the MCP server subprocess lifecycle.

    Usage::

        async with MCPClient() as client:
            tools = await client.list_tools()
            result = await client.call_tool("search_notes", {"query": "python"})
    """

    def __init__(self, server_script: Path | None = None) -> None:
        if server_script is None:
            server_script = (
                Path(__file__).parent.parent / "mcp_server" / "server.py"
            )
        self._server_script = server_script
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None

    async def __aenter__(self) -> "MCPClient":
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()

        params = StdioServerParameters(
            command=sys.executable,          # same Python venv as the client
            args=[str(self._server_script)],
            env=None,                        # inherit parent environment
        )

        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(params)
        )
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._exit_stack:
            await self._exit_stack.__aexit__(*exc_info)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def list_tools(self) -> list[dict]:
        """Return tool descriptors as plain dicts (name, description, input_schema)."""
        response = await self._session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema or {},
            }
            for tool in response.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """
        Call a named tool and return the parsed result.
        Tool results are JSON-decoded when possible; otherwise returned as raw text.
        """
        result = await self._session.call_tool(name, arguments)

        if not result.content:
            return None

        first = result.content[0]
        if not hasattr(first, "text"):
            return result.content

        text = first.text
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return text
