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
from prompts import DEVELOPER_PROMPT, LANGUAGE_INSTRUCTION, SYSTEM_PROMPT, TOOL_POLICY


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
        self._tools: list[dict] | None = None

    async def handle_query_stream(self, user_message: str, language: str = "en"):
        """
        Async generator that yields real-time events while processing.

        Yields dicts:
          {"type": "tool_start", "tool": name, "args": {...}}
          {"type": "tool_end",   "tool": name, "preview": "..."}
          {"type": "done",       "content": "final answer text"}
          {"type": "error",      "content": "error message"}

        Parameters
        ----------
        language : "en" | "ru" — response language for the model
        """
        tools = await self._ensure_tools()

        # Append language instruction so the model responds in the right language
        lang_note = LANGUAGE_INSTRUCTION.get(language, "")
        content = f"{user_message}\n\n{lang_note}" if lang_note else user_message
        self._messages.append({"role": "user", "content": content})

        try:
            for _round in range(self._config.max_tool_rounds):
                response = await self._model.chat(self._messages, tools)

                if response.has_tool_calls:
                    self._messages.append(
                        {
                            "role": "assistant",
                            "content": response.text or "",
                            "tool_calls": [
                                {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                                for tc in response.tool_calls
                            ],
                        }
                    )
                    for tc in response.tool_calls:
                        yield {"type": "tool_start", "tool": tc.name, "args": tc.arguments}
                        result = await self._mcp.call_tool(tc.name, tc.arguments)
                        result_str = (
                            json.dumps(result, ensure_ascii=False)
                            if not isinstance(result, str)
                            else result
                        )
                        yield {"type": "tool_end", "tool": tc.name, "preview": result_str[:120]}
                        self._messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "name": tc.name,
                                "content": result_str,
                            }
                        )
                else:
                    text = response.text.strip()
                    self._messages.append({"role": "assistant", "content": text})
                    yield {"type": "done", "content": text}
                    return

            yield {"type": "done", "content": "[Error: maximum number of steps exceeded]"}

        except Exception as exc:
            yield {"type": "error", "content": str(exc)}

    async def handle_query(self, user_message: str, language: str = "en") -> str:
        """Blocking version used by the CLI."""
        tools = await self._ensure_tools()
        lang_note = LANGUAGE_INSTRUCTION.get(language, "")
        content = f"{user_message}\n\n{lang_note}" if lang_note else user_message
        self._messages.append({"role": "user", "content": content})

        for _round in range(self._config.max_tool_rounds):
            response = await self._model.chat(self._messages, tools)

            if response.has_tool_calls:
                self._messages.append(
                    {
                        "role": "assistant",
                        "content": response.text or "",
                        "tool_calls": [
                            {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                            for tc in response.tool_calls
                        ],
                    }
                )
                for tc in response.tool_calls:
                    result = await self._mcp.call_tool(tc.name, tc.arguments)
                    result_str = (
                        json.dumps(result, ensure_ascii=False)
                        if not isinstance(result, str)
                        else result
                    )
                    self._messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": result_str,
                        }
                    )
            else:
                text = response.text.strip()
                self._messages.append({"role": "assistant", "content": text})
                return text

        return "[Error: maximum number of steps exceeded without a final answer]"

    async def _ensure_tools(self) -> list[dict]:
        if self._tools is None:
            self._tools = await self._mcp.list_tools()
        return self._tools

