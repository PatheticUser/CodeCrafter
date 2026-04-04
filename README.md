# CodeCrafter

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

CodeCrafter is a local AI coding agent that runs in your terminal. It reads, writes, executes, and debugs code in a sandboxed workspace — powered by [Ollama](https://ollama.com) cloud models for fast, private inference with automatic model fallback.

## Key Features

- **Multi-Language Execution** — Run Python, C++, JavaScript, HTML/CSS, and more directly from the CLI
- **Automatic Model Fallback** — If a model hits rate limits or errors out, seamlessly switches to the next one in the chain
- **Intelligent Workspace** — Auto-creates project folders, isolates scripts, maintains workspace context
- **Persistent Sessions** — Full conversation history preserved across restarts
- **Self-Correcting** — Automatically detects errors, installs missing dependencies, and retries
- **Sandboxed Security** — Path traversal protection and dangerous command blocklist keep operations safe

## Installation

### Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- [Ollama](https://ollama.com) installed and running

### Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
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
uv run main.py
```

For verbose mode with step-by-step tool inspection:
```bash
uv run main.py --verbose
```

Use a specific model:
```bash
uv run main.py --model qwen3-coder
```

### In-Agent Commands

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
# Use a shortcut
uv run main.py --model nemotron-super

# Or any Ollama model directly
uv run main.py --model llama3:latest
```

**Model shortcuts:** `qwen3.5`, `qwen3-coder`, `nemotron-super`

To customize the fallback chain, edit `FALLBACK_MODELS` in `config.py`.

## Architecture

```
CodeCrafter/
├── main.py              # Core agent loop and CLI
├── config.py            # Configuration (models, limits, UI)
├── core/
│   ├── api_manager.py   # Ollama client + model fallback
│   └── workspace.py     # Workspace tree scanning
├── ui/                  # Terminal interface and ANSI formatting
├── chat_session/        # Session persistence
├── functions/           # Tool implementations
│   ├── get_files_info   # List workspace files
│   ├── get_file_content # Read file contents
│   ├── get_file_outline # File structure overview
│   ├── write_file       # Create new files
│   ├── edit_file        # Modify existing files
│   ├── delete_file      # Remove files
│   ├── run_code         # Execute code (auto-detects language)
│   ├── run_command      # Run shell commands
│   └── search_files     # Grep-like pattern search
├── sessions/            # Session storage (gitignored)
└── workspace/           # Sandboxed working directory
```

## Configuration

All settings live in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama API endpoint |
| `DEFAULT_MODEL` | `qwen3.5:cloud` | Primary model |
| `FALLBACK_MODELS` | `[qwen3.5, qwen3-coder-next, nemotron-3-super]` | Model fallback chain |
| `MAX_TOKENS` | `4096` | Max tokens per response |
| `MAX_AGENT_STEPS` | `25` | Max tool steps per turn |
| `MAX_AUTO_FIX` | `3` | Auto-fix retry attempts |

## Security

CodeCrafter executes code on your local machine with these safeguards:

- **Workspace Confinement** — File operations are restricted to the `/workspace` directory with path traversal protection
- **Command Blocklist** — Destructive patterns (`rm -rf /`, `mkfs`, etc.) and access to sensitive paths are blocked

> **Disclaimer**: Always review the code the agent writes before executing shell commands in production environments.

## Contributing

Contributions are welcome! Fork the repository, create a feature branch, and submit a pull request.

## License

This project is open-sourced under the [MIT License](LICENSE).
