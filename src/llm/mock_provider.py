"""Deterministic Mock LLM Provider for unit and integration testing."""

from __future__ import annotations

from typing import Any

from src.llm.protocol import LLMProvider, LLMResponse, ToolCallRequest


class MockLLMProvider(LLMProvider):
    """Mock provider with queueable responses and request recording."""

    def __init__(self, default_model: str = "mock-model"):
        self.model = default_model
        self.response_queue: list[LLMResponse | Exception] = []
        self.recorded_calls: list[dict[str, Any]] = []

    def queue_response(self, response: LLMResponse | Exception) -> None:
        """Enqueue a scripted response or exception to return next."""
        self.response_queue.append(response)

    def queue_text(self, text: str, finish_reason: str = "stop") -> None:
        """Enqueue a simple text response."""
        self.queue_response(
            LLMResponse(
                content=text,
                tool_calls=[],
                finish_reason=finish_reason,
                usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                model=self.model,
            )
        )

    def queue_tool_call(
        self, name: str, arguments: dict[str, Any], call_id: str = "call_mock_1"
    ) -> None:
        """Enqueue a tool call response."""
        self.queue_response(
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id=call_id,
                        name=name,
                        arguments=arguments,
                        raw_arguments=str(arguments),
                    )
                ],
                finish_reason="tool_calls",
                usage={"prompt_tokens": 15, "completion_tokens": 10, "total_tokens": 25},
                model=self.model,
            )
        )

    def queue_multi_tool_calls(self, calls: list[tuple[str, dict[str, Any]]]) -> None:
        """Enqueue multiple tool calls in a single response."""
        tool_requests = [
            ToolCallRequest(
                id=f"call_mock_{i}",
                name=name,
                arguments=args,
                raw_arguments=str(args),
            )
            for i, (name, args) in enumerate(calls, 1)
        ]
        self.queue_response(
            LLMResponse(
                content="",
                tool_calls=tool_requests,
                finish_reason="tool_calls",
                usage={"prompt_tokens": 20, "completion_tokens": 20, "total_tokens": 40},
                model=self.model,
            )
        )

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        self.recorded_calls.append(
            {
                "messages": messages,
                "tools": tools,
                "temperature": temperature,
            }
        )

        if self.response_queue:
            next_item = self.response_queue.pop(0)
            if isinstance(next_item, Exception):
                raise next_item
            return next_item

        return LLMResponse(
            content="Mock LLM default response.",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
            model=self.model,
        )
