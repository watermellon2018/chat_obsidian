"""
Ollama model backend for local inference.

Recommended model (6 GB VRAM, best tool-calling):
    qwen2.5:7b-instruct-q4_K_M  (~4.5 GB)

Fallback (lower VRAM):
    llama3.2:3b                  (~3 GB)

Setup:
    1. Install Ollama: https://ollama.com/download
    2. Pull model: ollama pull qwen2.5:7b-instruct-q4_K_M
    3. Start server: ollama serve
"""
from __future__ import annotations

import uuid

import ollama

from config import Config
from model.base import BaseModel, ModelResponse, ToolCall


class OllamaModel(BaseModel):
    """Ollama backend using the async client."""

    def __init__(self, config: Config) -> None:
        self._model = config.ollama_model
        self._client = ollama.AsyncClient(host=config.ollama_base_url)

    # ------------------------------------------------------------------
    # Tool conversion (OpenAI-compatible format)
    # ------------------------------------------------------------------

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t.get(
                        "input_schema",
                        {"type": "object", "properties": {}},
                    ),
                },
            }
            for t in tools
        ]

    # ------------------------------------------------------------------
    # Message conversion
    # ------------------------------------------------------------------

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """
        Convert normalized messages to Ollama's format.
        Ollama uses OpenAI-compatible message roles.
        """
        converted = []
        for msg in messages:
            role = msg["role"]

            if role == "system":
                converted.append({"role": "system", "content": msg.get("content", "")})

            elif role == "user":
                converted.append({"role": "user", "content": msg.get("content", "")})

            elif role == "assistant":
                # Ollama expects tool_calls in the assistant message if present
                entry: dict = {"role": "assistant", "content": msg.get("content", "")}
                if msg.get("tool_calls"):
                    entry["tool_calls"] = [
                        {
                            "function": {
                                "name": tc["name"],
                                "arguments": tc.get("arguments", {}),
                            }
                        }
                        for tc in msg["tool_calls"]
                    ]
                converted.append(entry)

            elif role == "tool":
                converted.append(
                    {
                        "role": "tool",
                        "content": str(msg.get("content", "")),
                        "name": msg.get("name", "tool"),
                    }
                )

        return converted

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    async def chat(self, messages: list[dict], tools: list[dict]) -> ModelResponse:
        ollama_messages = self._convert_messages(messages)

        response = await self._client.chat(
            model=self._model,
            messages=ollama_messages,
            tools=self._convert_tools(tools),
        )

        msg = response.message
        tool_calls: list[ToolCall] = []

        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=str(uuid.uuid4()),
                        name=tc.function.name,
                        arguments=dict(tc.function.arguments)
                        if tc.function.arguments
                        else {},
                    )
                )

        return ModelResponse(
            text=msg.content or "",
            tool_calls=tool_calls,
            raw=response,
        )
