"""Inference client for CodeCrafter — calls Ollama directly via the OpenAI client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.api_manager import OllamaClient


# ---------------------------------------------------------------------------
# Dataclasses matching what main.py's agent loop expects
# ---------------------------------------------------------------------------


@dataclass
class FunctionCall:
    name: str
    arguments: str


@dataclass
class ToolCall:
    id: str
    type: str = "function"
    function: FunctionCall | None = None


@dataclass
class AssistantMessage:
    content: str | None = None
    tool_calls: list[ToolCall] | None = None


@dataclass
class Choice:
    message: AssistantMessage
    finish_reason: str = "stop"


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class CompletionResponse:
    choices: list[Choice] = field(default_factory=list)
    usage: Usage | None = None


# ---------------------------------------------------------------------------
# Inference Client — direct Ollama connection
# ---------------------------------------------------------------------------


class InferenceClient:
    """LLM inference client that calls Ollama directly via the OpenAI-compatible API.

    Wraps the OllamaClient for model fallback management and provides dataclass-based
    response types that main.py's agent loop uses.
    """

    def __init__(
        self,
        primary_model: str | None = None,
    ):
        self.ollama = OllamaClient(primary_model=primary_model)
        self.active_model = self.ollama.active_model

    def model_count(self) -> int:
        """Return total number of models in the fallback chain."""
        return self.ollama.model_count()

    def fallback(self) -> str | None:
        """Switch to the next model in the fallback chain."""
        new = self.ollama.fallback()
        if new:
            self.active_model = new
        return new

    def reset(self) -> None:
        """Reset back to the primary model."""
        self.ollama.reset()
        self.active_model = self.ollama.active_model

    # -----------------------------------------------------------------------
    # Chat completion
    # -----------------------------------------------------------------------

    def chat_completion(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | None = "auto",
        max_tokens: int = 4096,
    ) -> CompletionResponse:
        """Send a chat completion request directly to Ollama."""
        client = self.ollama.get_client()

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        response = client.chat.completions.create(**kwargs)

        # Parse response into our dataclasses
        choices: list[Choice] = []
        for c in response.choices:
            msg = c.message
            tool_calls = None
            if msg.tool_calls:
                tool_calls = [
                    ToolCall(
                        id=tc.id,
                        type=tc.type,
                        function=FunctionCall(
                            name=tc.function.name,
                            arguments=tc.function.arguments,
                        ),
                    )
                    for tc in msg.tool_calls
                ]

            assistant_msg = AssistantMessage(
                content=msg.content,
                tool_calls=tool_calls,
            )
            choices.append(Choice(message=assistant_msg, finish_reason=c.finish_reason))

        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            )

        return CompletionResponse(choices=choices, usage=usage)
