# CodeCrafter

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

CodeCrafter is a local AI coding agent that runs in your terminal. It reads, writes, executes, and debugs code in a sandboxed workspace — powered by [Ollama](https://ollama.com) cloud models for fast, private inference with automatic model fallback. Recently heavily refactored for production-ready reliability.

## Key Features

- **Multi-Language Execution** — Run Python, C++, JavaScript, HTML/CSS, and more directly from the CLI
- **Automatic Model Fallback** — If a model hits rate limits or errors out, seamlessly switches to the next one in the chain
- **Intelligent Workspace** — Auto-creates project folders, isolates scripts, maintains workspace context
- **Persistent Sessions** — Full conversation history preserved safely across restarts
- **Self-Correcting** — Automatically detects errors, installs missing dependencies, and retries natively via discrete loops
- **Sandboxed Security** — Path traversal protection and dangerous command blocklist keep operations safe
- **Modular Tool & Command Registries** — Clean architecture supporting easy extensibility

## Installation

### Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- [Ollama](https://ollama.com) installed and running

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/PatheticUser/CodeCrafter
   cd CodeCrafter
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Start Ollama:**
   ```bash
   ollama serve
   ```

   Cloud models are fetched automatically on first use — no need to pull manually.

## Usage

```bash
uv run codecrafter
# or
python main.py
```

For verbose mode with step-by-step tool inspection and logging:
```bash
python main.py --verbose
```

Use a specific model:
```bash
python main.py --model qwen3-coder
```

### Built-in Commands

| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `sessions` | List saved sessions |
| `session new` | Start a new session |
| `session load <name>` | Load a saved session |
| `session delete <name>` | Delete a session |
| `clear` | Clear current session history |
| `exit` / `quit` | Save and exit |

## Model Fallback

CodeCrafter uses a chain of Ollama cloud models. If the primary model fails (rate limit, unavailable, overloaded), it automatically switches to the next one:

| Priority | Model | Strengths |
|----------|-------|-----------|
| 1 (Primary) | `qwen3.5:cloud` | All-rounder — tools, vision, thinking |
| 2 | `qwen3-coder-next:cloud` | Coding-focused, agentic workflows |
| 3 | `nemotron-3-super:cloud` | NVIDIA 120B MoE, strong reasoning |

You can override the primary model with `--model`:

```bash
python main.py --model nemotron-super
python main.py --model llama3:latest
```

**Model shortcuts:** `qwen3.5`, `qwen3-coder`, `nemotron-super`

## Architecture

The architecture has been refactored for enterprise-level extensibility, inspired by `Claude Code`:

```
CodeCrafter/
├── main.py              # Thin CLI Entrypoint
├── config.py            # Centralized Configuration
├── core/
│   ├── agent.py         # AgentLoop (Agentic step orchestrator)
│   ├── api_manager.py   # Ollama client and model fallback
│   ├── workspace.py     # Workspace tree scanning
│   └── errors.py        # Error detection heuristics
├── tools/               # Agent Tools (BaseTool pattern & Registry)
│   ├── base.py
│   ├── run_code.py
│   ├── edit_file.py
│   └── ... (auto-discovered payload tools)
├── commands/            # CLI Command Handlers (CommandRegistry)
│   ├── base.py
│   ├── sessions.py
│   └── ...
├── services/            # Cross-cutting systems
│   ├── logger.py        # Structured logging
│   └── ...
├── chat_session/        # Session persistence and management
├── ui/                  # Terminal interface and ANSI formatting
└── workspace/           # Sandboxed execution directory
```

## Security

CodeCrafter executes code on your local machine with these safeguards:

- **Workspace Confinement** — File operations are restricted to the `/workspace` directory with path traversal protection
- **Command Blocklist** — Destructive patterns (`rm -rf /`, `mkfs`, etc.) and access to sensitive paths are blocked *(Note: Command safety uses a blocklist pattern, review code before letting it execute shell commands)*

> **Disclaimer**: Always review the code the agent writes before executing shell commands in production environments.

## License

This project is open-sourced under the [MIT License](LICENSE).
