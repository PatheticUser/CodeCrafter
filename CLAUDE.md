# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CodeCrafter is an educational AI coding agent that runs in your terminal. It connects to Ollama for LLM inference, using an OpenAI-compatible API. The agent can read, write, edit, and execute code in a sandboxed `workspace/` directory.

## Commands

```bash
# Install dependencies
uv sync

# Run the agent (original entry point)
uv run main.py
uv run main.py --verbose --model gpt-oss

# Run the refactored CLI entry point
uv run codecrafter

# Lint
uv run ruff check .
uv run ruff format --check .

# Auto-fix lint issues
uv run ruff check --fix .

# Run all tests with coverage
uv run pytest

# Run a single test file
uv run pytest tests/test_example.py

# Run a specific test
uv run pytest tests/test_example.py::test_function_name -v
```

## Architecture

There are **two parallel implementations** of the same agent. Understanding this is critical:

### Original Implementation (active, in use)

- `main.py` — Agent loop + CLI. The `build_system_prompt()` function constructs the LLM context. The main `while True` loop handles user input, calls the LLM, dispatches tool calls, and manages auto-fix/fallback.
- `config.py` — All configuration: model names, fallback chain, token limits, UI settings, error detection patterns.
- `functions/` — 9 tool implementations. Each exports an execute function + a JSON schema for the LLM. Tools are dispatched by name in `execute_tool()`.
- `core/api_manager.py` — `InferenceClient` wraps OpenAI SDK with automatic model fallback.
- `core/workspace.py` — `scan_workspace_tree()` generates a directory tree string injected into the system prompt.
- `ui/display.py` + `ui/spinner.py` — Terminal output formatting (colors, banners, action display, spinner).

### Refactored Implementation (`src/`)

A cleaner, class-based rewrite kept as a reference. Key differences:

- `src/core/agent.py` — `AgentLoop` class is transport-agnostic (could power CLI, API, or WebSocket). Uses `run_turn_streaming()` generator yielding `AgentResponse` dataclasses.
- `src/core/settings.py` — Pydantic-based settings (replaces `config.py`).
- `src/tools/` — Tool implementations with a `ToolRegistry` for registration and dispatch.
- `src/cli/` — CLI layer that consumes `AgentLoop`.

The refactored code is **not the primary entry point** but is being developed toward replacing `main.py`.

## Key Patterns

- **Agent loop**: LLM receives system prompt + conversation history → responds with tool calls or text → tool results fed back → repeat until final text response or max steps (25).
- **Model fallback**: On rate-limit/overload errors, `InferenceClient`/`OllamaClient` tries the next model in `FALLBACK_MODELS` chain.
- **Auto-fix**: When `run_code` or `run_command` produces an execution error (Traceback, SyntaxError, etc.), the agent injects a corrective user message and retries (up to 3 times).
- **Tool schemas**: Each tool in `functions/` or `src/tools/` defines a JSON schema (`schema_*`) that gets sent to the LLM as OpenAI-compatible function definitions.
- **Workspace confinement**: All file operations are restricted to `workspace/` with path traversal protection in `_security.py`.
- **Context trimming**: Long conversations are trimmed to the last 6 exchanges to prevent context overflow.

## Configuration

All runtime config lives in `config.py` (original) or `src/core/settings.py` (refactored). Key settings:

- `FALLBACK_MODELS` — Ordered model chain for automatic fallback
- `MAX_AGENT_STEPS` (25) — Max tool calls per user turn
- `MAX_AUTO_FIX` (3) — Max auto-retry on execution errors
- `WORKING_DIR` — Defaults to `workspace/`, override via `--path` or `CODECRAFTER_WORKING_DIR` env var

## Testing

Tests are in `tests/` using pytest with `pytest-asyncio` and `pytest-cov`. Coverage is configured for the `src/` directory. The test directory is currently empty — new tests should follow the existing `pyproject.toml` configuration.

## Linting

Ruff is configured with Python 3.11 target, 100-char line length, and rules: E, F, I, N, W, UP. Format uses double quotes.
