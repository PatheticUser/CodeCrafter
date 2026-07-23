# CodeCrafter

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Learn how AI coding agents work — by building one.**

CodeCrafter is an educational AI coding agent that runs in your terminal. You give it a prompt, and it reads, writes, executes, and debugs code in a sandboxed workspace — powered by [Ollama](https://ollama.com) cloud models with automatic fallback between models.

This project is structured to be **easy to read and understand**. The agent loop, tool execution, and LLM interaction are all visible in a few key files.

---

## Why Build This?

Commercial tools like Claude Code, Cursor, and GitHub Copilot hide their internals behind polished UIs. CodeCrafter shows you exactly what's happening:

- How an LLM decides what tools to call
- How tool results are fed back into the conversation
- How model fallback works when a model errors

- How workspace scanning gives the agent file awareness

Everything runs locally through [Ollama](https://ollama.com) — your code never leaves your machine.

---

## Quick Start

```bash
# 1. Clone & install
git clone https://github.com/PatheticUser/CodeCrafter
cd CodeCrafter
uv sync

# 2. Start Ollama (in another terminal)
ollama serve

# 3. Run the agent
uv run main.py
```

> **First run?** Cloud models are fetched automatically — no need to pull them manually.
> Type `help` in the agent to see available commands. Type `exit` to quit.

---

## Architecture

```
CodeCrafter/
├── main.py                           # Agent loop (LLM → tools → results → repeat)
├── config.py                         # All knobs: models, limits, UI settings
│
├── core/                             # LLM connection & workspace
│   ├── api_manager.py                #   Ollama client + model fallback chain
│   └── workspace.py                  #   Workspace tree scanner (context for the LLM)
│
├── functions/                        # 9 tools the agent can call
│   ├── get_files_info                #   List workspace files
│   ├── get_file_content              #   Read file (with line ranges)
│   ├── get_file_outline              #   File structure skeleton
│   ├── write_file                    #   Create files
│   ├── edit_file                     #   Surgical find-and-replace edits
│   ├── delete_file                   #   Remove files safely
│   ├── run_code                      #   Execute code (Python, JS, C++, Go, Rust, …)
│   ├── run_command                   #   Run shell commands (pip, npm, git, …)
│   └── search_files                  #   Grep-like pattern search
│

├── ui/                               # Terminal display
│   ├── display.py                    #   Colors, icons, banners, agent response
│   └── spinner.py                    #   Animated thinking spinner
│
└── workspace/                        # Sandbox for all file operations
```

### How the Agent Loop Works

This is the core flow, which you can trace through `main.py`:

```
1. User types a prompt
2. System prompt is built with workspace tree + tool definitions
3. LLM receives (system + conversation history + user prompt)
4. LLM responds with either:
   a. A tool call → tool executes → result sent back → goto 3
   b. A text answer → shown to user → turn ends
5. If tool execution errors → auto-fix injects a correction → goto 3
6. If model fails → fallback to next model in chain → goto 3
7. Session saved after each turn
```

---

## Usage

```bash
# Basic
uv run main.py

# Verbose — see every tool call, arguments, and result
uv run main.py --verbose

# Use a specific model
uv run main.py --model nemotron-super
```

### In-Agent Commands

| Command | Description |
|---------|-------------|
| `help` | Show available commands |

| `exit` / `quit` | Save and exit |

---

## Model Fallback

CodeCrafter chains multiple Ollama cloud models. If one fails (rate limit, unavailable, overloaded), it automatically tries the next:

| Priority | Model | Strengths |
|----------|-------|-----------|
| 1 (Primary) | `gpt-oss:120b-cloud` | Open-weight foundation model |
| 2 | `nemotron-3-super:cloud` | NVIDIA 120B MoE, strong reasoning |

Override with `--model`:

```bash
uv run main.py --model gpt-oss      # shortcut
uv run main.py --model llama3:latest # any Ollama model
```

**Shortcuts:** `gpt-oss`, `nemotron-super`

Edit the fallback chain in `config.py` → `FALLBACK_MODELS`.

---

## Configuration

All settings are in `config.py`. Key ones:

| Setting | Default | What it does |
|---------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama API endpoint |
| `DEFAULT_MODEL` | `gpt-oss:120b-cloud` | Primary model |
| `FALLBACK_MODELS` | 2 models | Ordered fallback chain |
| `MAX_TOKENS` | `4096` | Max tokens per LLM response |
| `MAX_AGENT_STEPS` | `25` | Max tool calls per user turn |
| `MAX_AUTO_FIX` | `3` | Auto-fix retry attempts |

---

## Also in This Repo

### `src/` — Alternative refactored structure

The `src/` directory contains a cleaner, class-based rewrite of the same agent:

- `src/core/agent.py` — `AgentLoop` class (transport-agnostic, could be used by CLI or API)
- `src/core/settings.py` — Pydantic-based settings (replaces `config.py`)
- `src/tools/` — Tool implementations (same as `functions/` but with a `ToolRegistry`)
- `src/cli/` — CLI display layer (same as `ui/`)

This structure was a refactoring exercise and is kept as a reference for comparing code architectures.

### `Landing-Page/` — Separate Next.js landing page

A standalone Next.js project with a cream/coral editorial design system. Not related to the agent.

---

## Security

CodeCrafter runs code on your machine with:

- **Workspace confinement** — all file operations restricted to `workspace/` with path traversal protection
- **Command blocklist** — `rm -rf /`, `mkfs`, `shutdown`, and other destructive patterns are blocked

> **Heads up:** Always review shell commands the agent writes before running in production.

---

## License

[MIT](LICENSE)
