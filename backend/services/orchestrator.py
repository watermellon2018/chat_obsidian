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
        self._tools: list[dict] | None = None

    async def handle_query_stream(self, user_message: str):
        """
        Async generator that yields real-time events while processing.

        Yields dicts:
          {"type": "tool_start", "tool": name, "args": {...}}
          {"type": "tool_end",   "tool": name, "preview": "..."}
          {"type": "done",       "content": "final answer text"}
          {"type": "error",      "content": "error message"}
        """
        tools = await self._ensure_tools()
        self._messages.append({"role": "user", "content": user_message})

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

            yield {"type": "done", "content": "[Ошибка: превышено максимальное количество шагов]"}

        except Exception as exc:
            yield {"type": "error", "content": str(exc)}

    async def handle_query(self, user_message: str) -> str:
        """Blocking version used by the CLI."""
        tools = await self._ensure_tools()
        self._messages.append({"role": "user", "content": user_message})

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

        return "[Ошибка: превышено максимальное количество шагов без финального ответа]"

    async def _ensure_tools(self) -> list[dict]:
        if self._tools is None:
            self._tools = await self._mcp.list_tools()
        return self._tools


# ------------------------------------------------------------------
# Flashcard generation (standalone — does not touch chat history)
# ------------------------------------------------------------------

async def generate_flashcard(
    model: BaseModel,
    mcp_client: MCPClient,
    config: Config,
    exclude: list[str] | None = None,
) -> dict:
    """
    Pick a random vault note and generate a Q&A flashcard via the model.

    Returns: {"question": "...", "answer": "...", "source": "path"}

    RAG hook: in the future, replace the random note selection with a
    retrieval step from services.retrieval.RetrievalService.
    """
    import random

    from prompts import FLASHCARD_PROMPT

    notes_raw = await mcp_client.call_tool("list_notes", {})
    notes: list[dict] = (
        json.loads(notes_raw) if isinstance(notes_raw, str) else notes_raw
    )

    candidates = [n for n in notes if n["path"] not in (exclude or [])]
    if not candidates:
        candidates = notes  # all seen → reset cycle

    note = random.choice(candidates)
    content_raw = await mcp_client.call_tool("read_note", {"path": note["path"]})
    content_obj: dict = (
        json.loads(content_raw) if isinstance(content_raw, str) else content_raw
    )
    note_text = content_obj.get("content", "")

    messages = [
        {"role": "system", "content": FLASHCARD_PROMPT},
        {"role": "user", "content": f"Note title: {note['title']}\n\n{note_text}"},
    ]
    response = await model.chat(messages, tools=[])
    raw_text = response.text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    card: dict = json.loads(raw_text)
    card["source"] = note["path"]
    return card
