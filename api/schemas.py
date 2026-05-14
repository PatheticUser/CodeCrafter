"""Pydantic schemas for the CodeCrafter Inference API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class FunctionCall(BaseModel):
    """A function/tool call from the LLM."""

    name: str
    arguments: str  # JSON string


class ToolCall(BaseModel):
    """A tool call from the LLM."""

    id: str
    type: str = "function"
    function: FunctionCall


class ChatMessage(BaseModel):
    """A single message in the chat conversation."""

    role: str  # "system", "user", "assistant", "tool"
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class ChatRequest(BaseModel):
    """Request to the chat completion endpoint."""

    model: str
    messages: list[ChatMessage]
    tools: list[dict[str, Any]] | None = None
    max_tokens: int = 4096
    stream: bool = True


class TokenUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatResponseChoice(BaseModel):
    """A single choice from the chat completion."""

    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatResponse(BaseModel):
    """Non-streaming chat completion response."""

    id: str
    model: str
    choices: list[ChatResponseChoice]
    usage: TokenUsage | None = None


class ChatChunk(BaseModel):
    """A streaming chunk from the chat completion."""

    id: str
    model: str
    choices: list[ChunkChoice]


class ChunkDelta(BaseModel):
    """Delta content in a streaming chunk."""

    content: str | None = None
    tool_calls: list[ToolCall] | None = None


class ChunkChoice(BaseModel):
    """A single choice in a streaming chunk."""

    index: int = 0
    delta: ChunkDelta
    finish_reason: str | None = None


class ModelInfo(BaseModel):
    """Information about an available model."""

    id: str
    active: bool = False
    available: bool = True


class ModelsResponse(BaseModel):
    """Response listing available models."""

    models: list[ModelInfo]
    active_model: str


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
