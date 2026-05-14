"""FastAPI server for the CodeCrafter Inference API.

Provides a stateless chat completion endpoint that wraps Ollama's API,
with streaming support and model fallback management.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from sse_starlette.sse import EventSourceResponse

from api.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    FunctionCall,
    ModelInfo,
    ModelsResponse,
    TokenUsage,
    ToolCall,
)
from config import DEFAULT_MODEL, OLLAMA_BASE_URL

# ---------------------------------------------------------------------------
# App state
# ---------------------------------------------------------------------------


class AppState:
    """Shared application state."""

    def __init__(self) -> None:
        self.client: AsyncOpenAI | None = None
        self.active_model = DEFAULT_MODEL

    def get_client(self) -> AsyncOpenAI:
        """Get or initialize the async OpenAI client."""
        if self.client is None:
            self.client = AsyncOpenAI(
                base_url=OLLAMA_BASE_URL,
                api_key="ollama",
            )
        return self.client


state: AppState | None = None


def get_state() -> AppState:
    assert state is not None, "App not initialized"
    return state


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    global state
    state = AppState()
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CodeCrafter Inference API",
    version="3.0.0",
    description="Stateless LLM inference API with streaming support for CodeCrafter",
    lifespan=lifespan,
)

# Allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper: convert API ChatMessage -> OpenAI message dict
# ---------------------------------------------------------------------------


def _to_openai_messages(messages: list[ChatMessage]) -> list[dict]:
    result: list[dict] = []
    for msg in messages:
        d: dict = {"role": msg.role}
        if msg.content is not None:
            d["content"] = msg.content
        if msg.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        if msg.tool_call_id:
            d["tool_call_id"] = msg.tool_call_id
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Helper: extract tool calls from OpenAI response
# ---------------------------------------------------------------------------


def _extract_tool_calls(openai_tool_calls) -> list[ToolCall] | None:
    """Extract ToolCall list from an OpenAI response message."""
    if not openai_tool_calls:
        return None
    return [
        ToolCall(
            id=tc.id,
            type=tc.type,
            function=FunctionCall(
                name=tc.function.name,
                arguments=tc.function.arguments,
            ),
        )
        for tc in openai_tool_calls
    ]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/v1/health")
async def health():
    """Health check endpoint."""
    s = get_state()
    return {
        "status": "ok",
        "model": s.active_model,
    }


@app.get("/api/v1/models", response_model=ModelsResponse)
async def list_models():
    """List available models."""
    s = get_state()
    return ModelsResponse(
        models=[ModelInfo(id="qwen3.5:cloud", active=True)],
        active_model=s.active_model,
    )


@app.post("/api/v1/chat")
async def chat_completion(request: ChatRequest):
    """Chat completion endpoint.

    Supports both streaming (SSE) and non-streaming responses.
    The client drives the agent loop — this is a single LLM call.
    """
    s = get_state()
    openai_messages = _to_openai_messages(request.messages)

    kwargs = {
        "model": request.model or s.active_model,
        "messages": openai_messages,
        "max_tokens": request.max_tokens,
        "stream": request.stream,
    }
    if request.tools:
        kwargs["tools"] = request.tools
        kwargs["tool_choice"] = "auto"

    try:
        if request.stream:
            return EventSourceResponse(_stream_chat(kwargs, request.model or s.active_model))
        else:
            return await _non_streaming_chat(kwargs, request.model or s.active_model)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Streaming handler
# ---------------------------------------------------------------------------


async def _stream_chat(kwargs: dict, model: str) -> AsyncGenerator[dict, None]:
    """SSE streaming generator using AsyncOpenAI."""
    s = get_state()
    response_id = f"chatcmpl-{int(time.time())}"

    try:
        client = s.get_client()
        stream = await client.chat.completions.create(**kwargs)

        async for chunk in stream:
            if chunk.choices:
                choice = chunk.choices[0]
                delta = choice.delta

                # Build SSE data payload
                data: dict = {
                    "id": response_id,
                    "model": model,
                    "choices": [
                        {
                            "index": choice.index,
                            "delta": {},
                            "finish_reason": choice.finish_reason,
                        }
                    ],
                }

                if delta.content:
                    data["choices"][0]["delta"]["content"] = delta.content

                if delta.tool_calls:
                    data["choices"][0]["delta"]["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in delta.tool_calls
                    ]

                yield {"event": "chat_chunk", "data": json.dumps(data)}

            # Send usage info on final chunk
            if hasattr(chunk, "usage") and chunk.usage:
                usage_data = {
                    "id": response_id,
                    "model": model,
                    "usage": {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    },
                }
                yield {"event": "usage", "data": json.dumps(usage_data)}

        # Signal done
        yield {"event": "done", "data": json.dumps({"id": response_id, "model": model})}

    except Exception as exc:
        yield {
            "event": "error",
            "data": json.dumps({"error": str(exc)}),
        }


# ---------------------------------------------------------------------------
# Non-streaming handler
# ---------------------------------------------------------------------------


async def _non_streaming_chat(kwargs: dict, model: str) -> ChatResponse:
    """Non-streaming (blocking) chat completion using AsyncOpenAI."""
    s = get_state()
    kwargs["stream"] = False
    client = s.get_client()
    response = await client.chat.completions.create(**kwargs)

    choice = response.choices[0]
    msg = choice.message

    tool_calls = _extract_tool_calls(msg.tool_calls)
    chat_msg = ChatMessage(
        role="assistant",
        content=msg.content,
        tool_calls=tool_calls,
    )

    usage = None
    if hasattr(response, "usage") and response.usage:
        usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

    return ChatResponse(
        id=f"chatcmpl-{int(time.time())}",
        model=model,
        choices=[ChatResponseChoice(message=chat_msg, finish_reason=choice.finish_reason)],
        usage=usage,
    )
