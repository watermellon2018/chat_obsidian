"""Abstract base classes for model backends."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ToolCall:
    """Normalized representation of a model's request to call a tool."""

    __slots__ = ("id", "name", "arguments")

    def __init__(self, id: str, name: str, arguments: dict[str, Any]) -> None:
        self.id = id
        self.name = name
        self.arguments = arguments

    def __repr__(self) -> str:
        return f"ToolCall(name={self.name!r}, arguments={self.arguments!r})"


class ModelResponse:
    """
    Normalized response from any model backend.

    * ``tool_calls`` is non-empty when the model wants to call one or more tools.
    * ``text`` is non-empty when the model produces a final text answer.
    """

    __slots__ = ("text", "tool_calls", "raw")

    def __init__(
        self,
        text: str = "",
        tool_calls: list[ToolCall] | None = None,
        raw: Any = None,
    ) -> None:
        self.text = text
        self.tool_calls: list[ToolCall] = tool_calls or []
        self.raw = raw

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseModel(ABC):
    """
    Abstract interface that all model backends must implement.

    The orchestrator calls ``chat()`` with the full message history and the list
    of available tools, then inspects the returned ``ModelResponse`` to decide
    whether to execute tool calls or surface the final text answer.

    Message format (shared across backends):

    .. code-block:: python

        # System instruction
        {"role": "system", "content": "..."}

        # User turn
        {"role": "user", "content": "..."}

        # Assistant turn — text answer
        {"role": "assistant", "content": "..."}

        # Assistant turn — tool call(s)
        {"role": "assistant", "content": "",
         "tool_calls": [{"id": "...", "name": "...", "arguments": {...}}]}

        # Tool result
        {"role": "tool", "tool_call_id": "...", "name": "...", "content": "..."}
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> ModelResponse:
        """Send the full conversation history and return a ModelResponse."""
        ...
