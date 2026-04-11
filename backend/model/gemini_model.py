"""
Google Gemini model backend (google-genai SDK).

Free tier: gemini-2.0-flash — 15 RPM, 1 000 000 TPM, 1 500 requests/day
Get API key: https://aistudio.google.com → "Get API key"
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any

from google import genai
from google.genai import types

from config import Config
from model.base import BaseModel, ModelResponse, ToolCall


class GeminiModel(BaseModel):
    """Gemini backend using the stateless generate_content API."""

    def __init__(self, config: Config) -> None:
        self._client = genai.Client(api_key=config.gemini_api_key)
        self._model_name = config.gemini_model

    def _convert_tools(self, tools: list[dict]) -> list[types.Tool]:
        declarations = []
        for t in tools:
            schema = t.get("input_schema", {})
            props = {}
            for k, v in schema.get("properties", {}).items():
                props[k] = {sk: sv for sk, sv in v.items() if sk != "title"}

            declarations.append(
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters={
                        "type": "OBJECT",
                        "properties": props,
                        "required": schema.get("required", []),
                    },
                )
            )
        return [types.Tool(function_declarations=declarations)]

    def _build_contents(
        self, messages: list[dict]
    ) -> tuple[str, list[types.Content]]:
        system_parts: list[str] = []
        contents: list[types.Content] = []

        for msg in messages:
            role = msg["role"]
            content_str = msg.get("content", "")

            if role == "system":
                if content_str:
                    system_parts.append(content_str)

            elif role == "user":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part(text=content_str or " ")],
                    )
                )

            elif role == "assistant":
                parts: list[types.Part] = []
                for tc in msg.get("tool_calls", []):
                    parts.append(
                        types.Part(
                            function_call=types.FunctionCall(
                                id=tc.get("id", ""),
                                name=tc["name"],
                                args=tc.get("arguments", {}),
                            )
                        )
                    )
                if content_str:
                    parts.append(types.Part(text=content_str))
                if parts:
                    contents.append(types.Content(role="model", parts=parts))

            elif role == "tool":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=msg.get("name", "tool"),
                                response={"result": content_str},
                            )
                        ],
                    )
                )

        return "\n\n".join(system_parts), contents

    async def chat(self, messages: list[dict], tools: list[dict]) -> ModelResponse:
        system_instruction, contents = self._build_contents(messages)

        last_exc: Exception | None = None
        for attempt in range(5):
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction or None,
                        tools=self._convert_tools(tools),
                    ),
                )
                break
            except Exception as exc:
                last_exc = exc
                if "429" in str(exc) and attempt < 4:
                    wait = 2 ** attempt
                    print(f"  [gemini] rate-limited, retrying in {wait}s…")
                    await asyncio.sleep(wait)
                else:
                    raise
        else:
            raise last_exc

        candidate = response.candidates[0]
        tool_calls: list[ToolCall] = []
        text_parts: list[str] = []

        for part in candidate.content.parts:
            if part.function_call and part.function_call.name:
                fc = part.function_call
                tool_calls.append(
                    ToolCall(
                        id=getattr(fc, "id", None) or str(uuid.uuid4()),
                        name=fc.name,
                        arguments=dict(fc.args) if fc.args else {},
                    )
                )
            elif part.text:
                text_parts.append(part.text)

        return ModelResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            raw=response,
        )
