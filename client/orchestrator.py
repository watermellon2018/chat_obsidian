"""
Agentic tool-calling loop.

Manages the conversation history and mediates between the model backend
and the MCP client. Enforces the mandatory 4-step execution flow:

  1. Receive user query
  2. Model calls MCP tools (search → read → …)
  3. Model analyzes results
  4. Model generates final response
"""
from __future__ import annotations

import json

from client.mcp_client import MCPClient
from config import Config
from model.base import BaseModel
from prompts import DEVELOPER_PROMPT, SYSTEM_PROMPT, TOOL_POLICY


class Orchestrator:
    """One chat session. Owns the message history and the agentic loop."""

    def __init__(
        self, model: BaseModel, mcp_client: MCPClient, config: Config
    ) -> None:
        self._model = model
        self._mcp = mcp_client
        self._config = config
        self._messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": DEVELOPER_PROMPT + "\n\n" + TOOL_POLICY},
        ]
        self._tools: list[dict] | None = None  # cached after first fetch

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def handle_query(self, user_message: str) -> str:
        """
        Process one user turn through the full agentic loop.
        Returns the assistant's final text response.
        """
        tools = await self._ensure_tools()
        self._messages.append({"role": "user", "content": user_message})

        for _round in range(self._config.max_tool_rounds):
            response = await self._model.chat(self._messages, tools)

            if response.has_tool_calls:
                # Record the assistant's intent (tool calls) in history
                self._messages.append(
                    {
                        "role": "assistant",
                        "content": response.text or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "name": tc.name,
                                "arguments": tc.arguments,
                            }
                            for tc in response.tool_calls
                        ],
                    }
                )

                # Execute each tool via MCP and append results
                for tc in response.tool_calls:
                    _print_tool_call(tc.name, tc.arguments)
                    result = await self._mcp.call_tool(tc.name, tc.arguments)
                    result_str = (
                        json.dumps(result, ensure_ascii=False)
                        if not isinstance(result, str)
                        else result
                    )
                    _print_tool_result(result_str)

                    self._messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": result_str,
                        }
                    )

            else:
                # Final text answer
                text = response.text.strip()
                self._messages.append({"role": "assistant", "content": text})
                return text

        return (
            "[Error: reached maximum tool-calling rounds without a final answer. "
            "The vault may not contain relevant information.]"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_tools(self) -> list[dict]:
        if self._tools is None:
            self._tools = await self._mcp.list_tools()
        return self._tools


# ------------------------------------------------------------------
# Display helpers (printed to stdout so the user can see tool usage)
# ------------------------------------------------------------------

def _fmt_args(args: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


def _print_tool_call(name: str, args: dict) -> None:
    print(f"  \033[90m[tool] {name}({_fmt_args(args)})\033[0m")


def _print_tool_result(result_str: str) -> None:
    preview = result_str[:150] + ("…" if len(result_str) > 150 else "")
    print(f"  \033[90m[result] {preview}\033[0m")
