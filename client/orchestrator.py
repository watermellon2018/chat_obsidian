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

            yield {"type": "done", "content": "[Error: reached maximum tool-calling rounds]"}

        except Exception as exc:
            yield {"type": "error", "content": str(exc)}

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


# ------------------------------------------------------------------
# Flashcard generation (standalone — does not touch chat history)
# ------------------------------------------------------------------

async def generate_flashcard(
    model: "BaseModel",
    mcp_client: "MCPClient",
    config: "Config",
    exclude: list[str] | None = None,
) -> dict:
    """
    Pick a random vault note and generate a Q&A flashcard via the model.

    Returns: {"question": "...", "answer": "...", "source": "path"}
    """
    import random

    from prompts import FLASHCARD_PROMPT

    # 1. List all notes via MCP
    notes_raw = await mcp_client.call_tool("list_notes", {})
    notes: list[dict] = (
        json.loads(notes_raw) if isinstance(notes_raw, str) else notes_raw
    )

    # 2. Exclude already-seen paths; reset if all seen
    candidates = [n for n in notes if n["path"] not in (exclude or [])]
    if not candidates:
        candidates = notes

    # 3. Pick a random note and read its content
    note = random.choice(candidates)
    content_raw = await mcp_client.call_tool("read_note", {"path": note["path"]})
    content_obj: dict = (
        json.loads(content_raw) if isinstance(content_raw, str) else content_raw
    )
    note_text = content_obj.get("content", "")

    # 4. Ask model to produce flashcard JSON (no MCP tools, just text generation)
    messages = [
        {"role": "system", "content": FLASHCARD_PROMPT},
        {"role": "user", "content": f"Note title: {note['title']}\n\n{note_text}"},
    ]
    response = await model.chat(messages, tools=[])
    raw_text = response.text.strip()

    # 5. Parse JSON — strip markdown fences if the model adds them
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    card: dict = json.loads(raw_text)
    card["source"] = note["path"]
    return card
