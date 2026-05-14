"""Dual-mode inference client for CodeCrafter.

Tries the local API server first, falls back to direct Ollama connection
if the API server is unreachable.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

import requests

from core.api_manager import OllamaClient

# ---------------------------------------------------------------------------
# Simple dataclasses matching what main.py's agent loop needs
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
# API base URL (from env or default)
# ---------------------------------------------------------------------------

DEFAULT_API_URL = os.environ.get("CODECRAFTER_API_URL", "http://127.0.0.1:8000")


# ---------------------------------------------------------------------------
# Inference Client
# ---------------------------------------------------------------------------


class InferenceClient:
    """Dual-mode inference client.

    Uses the local API server when available, otherwise falls back to
    direct Ollama connection via the OpenAI client.
    """

    def __init__(
        self,
        api_url: str | None = None,
        primary_model: str | None = None,
        api_key: str | None = None,
    ):
        self.api_url = (api_url or DEFAULT_API_URL).rstrip("/")
        self.api_key = api_key or os.environ.get("CODECRAFTER_API_KEY", "")
        self.ollama = OllamaClient(primary_model=primary_model)
        self.active_model = self.ollama.active_model
        self._api_available: bool | None = None  # None = not yet checked
        self._last_check: float = 0.0  # timestamp of last API check

    # -----------------------------------------------------------------------
    # API availability
    # -----------------------------------------------------------------------

    def is_api_available(self, force_check: bool = False) -> bool:
        """Check if the API server is reachable.

        Results are cached after the first check to avoid hammering the
        server on every LLM call. Re-checks automatically after 30 seconds
        so a recovered server can be picked up.
        """
        now = time.monotonic()
        if self._api_available is not None and not force_check:
            # Re-check if enough time has passed since the last failure
            if self._api_available or (now - self._last_check < 30.0):
                return self._api_available

        try:
            headers: dict[str, str] = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.get(
                urljoin(self.api_url, "/api/v1/health"),
                headers=headers,
                timeout=1.5,
            )
            self._api_available = resp.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            self._api_available = False
        finally:
            self._last_check = now

        return self._api_available

    def model_count(self) -> int:
        return self.ollama.model_count()

    def fallback(self) -> str | None:
        """Switch to the next model in the fallback chain.

        Delegates to the underlying OllamaClient.
        """
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
        """Send a chat completion request.

        Tries the API server first. Falls back to direct Ollama if the
        API is unavailable.
        """
        if self.is_api_available():
            try:
                return self._api_chat_completion(
                    model=model,
                    messages=messages,
                    tools=tools,
                    max_tokens=max_tokens,
                )
            except Exception:
                # Fall through to direct on any API error
                self._api_available = False

        return self._direct_chat_completion(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
        )

    # -----------------------------------------------------------------------
    # API-mode completion
    # -----------------------------------------------------------------------

    def _api_chat_completion(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> CompletionResponse:
        """Call the local API server's non-streaming endpoint."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        url = urljoin(self.api_url, "/api/v1/chat")
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        return self._parse_api_response(data, model)

    def _parse_api_response(self, data: dict, model: str) -> CompletionResponse:
        """Parse the API response dict into our dataclasses."""
        choices: list[Choice] = []
        for c in data.get("choices", []):
            msg = c.get("message", {})
            tool_calls = None
            if msg.get("tool_calls"):
                tool_calls = [
                    ToolCall(
                        id=tc["id"],
                        type=tc.get("type", "function"),
                        function=FunctionCall(
                            name=tc["function"]["name"],
                            arguments=tc["function"]["arguments"],
                        ),
                    )
                    for tc in msg["tool_calls"]
                ]

            assistant_msg = AssistantMessage(
                content=msg.get("content"),
                tool_calls=tool_calls,
            )
            choices.append(
                Choice(message=assistant_msg, finish_reason=c.get("finish_reason", "stop"))
            )

        usage = None
        if data.get("usage"):
            usage = Usage(
                prompt_tokens=data["usage"]["prompt_tokens"],
                completion_tokens=data["usage"]["completion_tokens"],
            )

        return CompletionResponse(choices=choices, usage=usage)

    # -----------------------------------------------------------------------
    # Direct Ollama mode (existing behavior)
    # -----------------------------------------------------------------------

    def _direct_chat_completion(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | None = "auto",
        max_tokens: int = 4096,
    ) -> CompletionResponse:
        """Call Ollama directly via the OpenAI client."""
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
        return self._parse_openai_response(response)

    def _parse_openai_response(self, response: Any) -> CompletionResponse:
        """Parse the OpenAI SDK response into our dataclasses."""
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
