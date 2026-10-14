"""OpenAI-compatible chat completions provider with retries, jitter, and error normalization."""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any

from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError

from src.llm.protocol import LLMProvider, LLMResponse, ToolCallRequest

logger = logging.getLogger("codecrafter.llm")


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible inference provider supporting tool calling and retries."""

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str = "",
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 120.0,
        max_retries: int = 3,
        default_temperature: float | None = 0.2,
        extra_kwargs: dict[str, Any] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "sk-dummy-key"
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.default_temperature = default_temperature
        self.extra_kwargs = extra_kwargs or {}

        self._client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout_seconds,
            max_retries=0,  # We handle retries explicitly with backoff and jitter
        )

    def _is_transient_error(self, exc: Exception) -> bool:
        """Check if an exception represents a retryable transient failure."""
        if isinstance(exc, (APIConnectionError, RateLimitError, asyncio.TimeoutError)):
            return True
        if isinstance(exc, APIStatusError):
            # 429 rate limit, 500-504 server errors
            return exc.status_code in {429, 500, 502, 503, 504}
        err_msg = str(exc).lower()
        return any(
            x in err_msg
            for x in [
                "429",
                "rate limit",
                "overloaded",
                "503",
                "timeout",
                "temporarily unavailable",
            ]
        )

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Execute chat completion with exponential backoff and jitter."""
        temp = temperature if temperature is not None else self.default_temperature
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            **self.extra_kwargs,
        }
        if temp is not None:
            kwargs["temperature"] = temp
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                return self._parse_response(response)
            except Exception as exc:
                last_error = exc
                is_transient = self._is_transient_error(exc)
                if attempt < self.max_retries and is_transient:
                    # Exponential backoff: base * 2^attempt + jitter
                    backoff = (1.5**attempt) + random.uniform(0.1, 0.6)
                    logger.warning(
                        "LLM call failed transiently: %s. Retrying in %.2fs (attempt %d/%d)...",
                        exc,
                        backoff,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(backoff)
                    continue

                logger.error("LLM call failed permanently on attempt %d: %s", attempt + 1, exc)
                return LLMResponse(
                    error=f"LLM API error ({type(exc).__name__}): {exc}",
                    model=self.model,
                    finish_reason="error",
                )

        return LLMResponse(
            error=f"Max retries exceeded: {last_error}",
            model=self.model,
            finish_reason="error",
        )

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse raw OpenAI completion object into normalized LLMResponse."""
        if not response.choices:
            return LLMResponse(
                content="",
                model=getattr(response, "model", self.model),
                finish_reason="empty",
            )

        choice = response.choices[0]
        message = choice.message
        content = message.content or ""

        tool_calls: list[ToolCallRequest] = []
        if getattr(message, "tool_calls", None):
            for tc in message.tool_calls:
                raw_args = tc.function.arguments or "{}"
                try:
                    parsed_args = json.loads(raw_args)
                    if not isinstance(parsed_args, dict):
                        parsed_args = {"_raw": parsed_args}
                except (json.JSONDecodeError, TypeError) as decode_err:
                    logger.warning(
                        "Malformed tool arguments for '%s': %s", tc.function.name, decode_err
                    )
                    parsed_args = {"_error": f"Invalid JSON arguments: {raw_args}"}

                tool_calls.append(
                    ToolCallRequest(
                        id=tc.id or f"call_{random.randint(1000, 9999)}",
                        name=tc.function.name,
                        arguments=parsed_args,
                        raw_arguments=raw_args,
                    )
                )

        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0) or 0,
                "completion_tokens": getattr(response.usage, "completion_tokens", 0) or 0,
                "total_tokens": getattr(response.usage, "total_tokens", 0) or 0,
            }

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=getattr(choice, "finish_reason", "stop"),
            usage=usage,
            model=getattr(response, "model", self.model),
        )
