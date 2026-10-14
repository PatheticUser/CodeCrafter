"""LLM Provider abstraction and response protocols."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ToolCallRequest:
    """Represents a validated tool call requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    raw_arguments: str = ""


@dataclass
class LLMResponse:
    """Normalized response representation across any inference backend."""

    content: str | None = None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    finish_reason: str | None = None
    usage: dict[str, int] | None = None
    model: str = ""
    error: str | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM inference providers."""

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Execute a completion request and return normalized response."""
        ...
