"""
OpenRouter model backend (OpenAI-compatible API).

Supports any model available on https://openrouter.ai/models
Default: google/gemini-2.5-flash
"""
from __future__ import annotations

import json
import uuid

from openai import AsyncOpenAI

from config import Config
from model.base import BaseModel, ModelResponse, ToolCall


class OpenRouterModel(BaseModel):
    """OpenRouter backend using the OpenAI-compatible API."""

    def __init__(self, config: Config) -> None:
        self._client = AsyncOpenAI(
            api_key=config.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self._model_name = config.openrouter_model

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        result = []
        for t in tools:
            schema = t.get("input_schema", {})
            props = {}
            for k, v in schema.get("properties", {}).items():
                props[k] = {sk: sv for sk, sv in v.items() if sk != "title"}
            result.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": schema.get("required", []),
                    },
                },
            })
        return result

    def _build_messages(self, messages: list[dict]) -> list[dict]:
        result = []
        for msg in messages:
            role = msg["role"]
            if role in ("system", "user"):
                result.append({"role": role, "content": msg.get("content", "")})
            elif role == "assistant":
                m: dict = {"role": "assistant", "content": msg.get("content") or None}
                if msg.get("tool_calls"):
                    m["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc.get("arguments", {})),
                            },
                        }
                        for tc in msg["tool_calls"]
                    ]
                result.append(m)
            elif role == "tool":
                result.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", msg.get("id", "")),
                    "content": msg.get("content", ""),
                })
        return result

    async def chat(self, messages: list[dict], tools: list[dict]) -> ModelResponse:
        oai_messages = self._build_messages(messages)
        oai_tools = self._convert_tools(tools) if tools else []

        kwargs: dict = {"model": self._model_name, "messages": oai_messages}
        if oai_tools:
            kwargs["tools"] = oai_tools

        response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        msg = choice.message
        tool_calls: list[ToolCall] = []

        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id or str(uuid.uuid4()),
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments or "{}"),
                    )
                )

        return ModelResponse(
            text=msg.content or "",
            tool_calls=tool_calls,
            raw=response,
        )
