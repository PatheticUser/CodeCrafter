# CodeCrafter

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

CodeCrafter is a powerful, local command-line AI coding agent that reads, writes, executes, and debugs code in a sandboxed workspace. Built around the Groq API (powered by state-of-the-art models), it is designed for rapid prototyping, robust development assistance, and learning.

## Key Features

- **Multi-Language Execution**: Run Python, compile/execute C++, execute JavaScript (Node/Bun), and preview HTML/CSS directly from the CLI.
- **Intelligent Workspace Management**: Creates dedicated folders for projects and isolates single scripts seamlessly. Maintains context with auto-generated metadata.
- **Persistent Session Management**: Complete history of conversations kept outside the workspace. Pick up right where you left off.
- **Hardened Security Sandbox**: 
  - Path traversal protections ensure file operations stay exclusively within the sandbox.
  - Strict command blocklists prevent dangerous shell executions.
- **API Key Management**: Supports automatic rotation for Groq API keys to elegantly handle rate limits dynamically.

## Installation

### Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (Recommended) or `pip`
- [Groq API Key](https://console.groq.com)

### Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd CodeCrafter
   ```

2. **Install dependencies:**
    Using `uv`:
   ```bash
   uv sync
   ```
   Or using `pip`:
   ```bash
   pip install groq
   ```

3. **Configure API Keys:**
   Create an `api_keys.json` file in the project root containing your Groq API keys as a JSON array:
   ```json
   [
       "gsk_your_first_api_key_here",
       "gsk_your_second_api_key_here"
   ]
   ```

## Usage

Start the agent with `uv`:
```bash
uv run main.py
```

For verbose debugging and real-time tool inspection:
```bash
uv run main.py --verbose
```

**Commands inside the agent:**
- `help` - Show all available commands
- `sessions` / `session new` / `session load <name>` / `session delete <name>` - Manage chat sessions
- `clear` - Clear the current session history
- `exit` / `quit` - Save and exit

## Project Architecture

CodeCrafter maintains a clean separation of concerns:

```
CodeCrafter/
├── main.py                     # Core agent loop and CLI
├── config.py                   # Global configuration and security limits
├── core/                       # API key rotation, workspace scanning
├── ui/                         # Terminal interface and ANSI formatting
├── functions/                  # Tool implementations (read, write, exec)
├── sessions/                   # Session storage (gitignored)
└── workspace/                  # Sandboxed working directory
```

## Security

CodeCrafter executes code and shell commands on your local machine. It incorporates several safeguards:
- **Workspace Confinement**: Operations like file writes, reads, and deletes are statically verified against path-traversal within the `/workspace` directory.
- **Dangerous Command Blocklist**: Destructive execution patterns (e.g., `rm -rf /`, `mkfs`) and access to sensitive locations (`/etc/shadow`) are heavily restricted natively.

> **Disclaimer**: This tool is built for development purposes. Always review the code the agent intends to run, especially before executing shell commands.

## Contributing

Contributions are welcome! Please fork the repository, create a feature branch, and submit a pull request. Make sure tests are well documented.

## License

This project is open-sourced under the [MIT License](LICENSE).
