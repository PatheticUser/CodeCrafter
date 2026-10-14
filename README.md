# CodeCrafter

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Learn how AI coding agents work — and watch one work in your browser.**

CodeCrafter is an educational AI coding agent. Give it a prompt and it reads, writes, executes, and debugs code in a sandboxed workspace — powered by **any OpenAI-compatible external LLM API** (OpenAI, Groq, DeepSeek, Gemini, preserves your own endpoint, and more).

This project is structured to be **easy to read and understand**. The agent loop, tool execution, and LLM interaction are all visible in a few key files.

---

## Why Build This?

Commercial tools like Claude Code, Cursor, and GitHub Copilot hide their internals behind polished UIs. CodeCrafter shows you exactly what's happening:

- How an LLM decides what tools to call
- How tool results are fed back into the conversation
- How structured events stream from agent to browser in real time
- How workspace scanning gives the agent file awareness
- How workspace confinement keeps generated code isolated

---

## Quick Start

### Local development (backend + frontend)

```bash
# 1. Clone & install backend
git clone https://github.com/PatheticUser/CodeCrafter
cd CodeCrafter
uv sync

# 2. Configure inference
cp .env.example .env
# edit .env: set LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

# 3. Start the backend (FastAPI on :8000)
uv run uvicorn src.api.app:app --host 127.0.0.1 --port 8000

# 4. Start the frontend (Next.js on :3000)
cd Landing-Page
npm install
npm run dev
```

Open **http://localhost:3000** to explore, then **http://localhost:3000/workspace** to use the coding environment.

### Docker Compose

```bash
cp .env.example .env.production
# edit .env.production with your API credentials
docker compose --env-file .env.production up -d --build
```

### Terminal CLI (optional adapter, same agent core)

```bash
uv run main.py
```

---

## Architecture

```
CodeCrafter/
├── src/                              # Canonical backend implementation
│   ├── core/
│   │   ├── agent.py                  #   CodingAgent — async multi-step loop, emits AgentEvent
│   │   ├── events.py                 #   Structured event types (agent.started, tool.completed, …)
│   │   └── settings.py               #   Pydantic Settings (env-driven config)
│   ├── llm/
│   │   ├── protocol.py               #   LLMProvider protocol + normalized LLMResponse
│   │   ├── openai_provider.py        #   OpenAI-compatible Chat Completions w/ backoff retries
│   │   └── mock_provider.py          #   Deterministic mock for tests (no paid inference)
│   ├── workspace/
│   │   ├── base.py                   #   Workspace protocol
│   │   ├── local.py                  #   LocalWorkspace (host directory)
│   │   ├── docker.py                 #   DockerWorkspace (isolated container execution)
│   │   ├── security.py               #   Path traversal/symlink protection + command gating
│   │   └── manager.py                #   Per-project workspace lifecycle
│   ├── api/
│   │   ├── app.py                    #   FastAPI app, CORS, bearer-token auth
│   │   ├── run_manager.py            #   Run state machine, cancellation, event broadcast
│   │   └── routes/                   #   health, projects, sessions, agent runs + WebSocket
│   ├── tools/                        # 9 tools (registry-based dispatch)
│   ├── db/database.py                # SQLite persistence (projects, sessions, runs, events)
│   └── cli/main.py                   # CLI adapter over the same agent core
│
├── Landing-Page/                     # Next.js frontend
│   └── app/workspace/                # Dashboard + coding environment (chat, files, Monaco)
│
├── main.py                           # Terminal CLI entry point (uses same agent core)
├── config.py                         # Legacy CLI config
├── Dockerfile                        # Backend container image
└── docker-compose.yml                # Full stack: app + Caddy reverse proxy
```

### How the Agent Loop Works

This is the core flow, which you can trace through `src/core/agent.py`:

```
1. User submits a prompt (browser → POST /api/agent/runs)
2. Run is created (pending → running), background task starts
3. System prompt is built with workspace tree + tool definitions
4. LLM receives (system + conversation history + user prompt)
5. LLM responds with either:
   a. Tool call(s) → executed against workspace → results appended → goto 4
   b. Text answer → streamed to browser → run completed
6. If tool execution errors → auto-fix injects a correction → goto 4
7. Every step is broadcast as a structured event, persisted, and
   streamed to the browser over WebSocket (with replay on reconnect)
```

---

## API Overview

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Service health + version |
| `POST /api/projects` | Create empty project |
| `POST /api/projects/import-git` | Import public repository by URL |
| `GET /api/projects/{id}/files` | File listing + directory tree |
| `GET/PUT /api/projects/{id}/files/content` | Read / save file content |
| `POST /api/sessions` | Create conversation session |
| `GET /api/sessions/{id}` | Session + full message history |
| `POST /api/agent/runs` | Start agent run (202 + run_id) |
| `POST /api/agent/runs/{id}/cancel` | Cancel active run |
| `WS /api/agent/runs/{id}/events` | Stream events (supports `?since=` replay) |

All endpoints accept an optional `Authorization: Bearer <API_TOKEN>` when `API_TOKEN` is configured.

---

## Configuration

All configuration is environment-driven via `src/core/settings.py` (see `.env.example`). Key variables:

| Variable | Default | What it does |
|----------|---------|-------------|
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compatible endpoint |
| `LLM_API_KEY` | — | API key for the provider |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `LLM_TIMEOUT_SECONDS` | `120` | Per-request timeout |
| `LLM_MAX_RETRIES` | `3` | Transient-error retries (exp. backoff + jitter) |
| `LLM_TEMPERATURE` | `0.2` | Set empty to send no temperature |
| `MAX_AGENT_STEPS` | `25` | Max tool calls per user turn |
| `MAX_AUTO_FIX` | `3` | Auto-fix retry attempts |
| `WORKSPACE_BACKEND` | `local` | `local` or `docker` execution backend |
| `WORKSPACE_ROOT` | `./workspace` | Where project workspaces live |
| `WORKSPACE_COMMAND_TIMEOUT` | `60` | Command timeout (seconds) |
| `DATABASE_URL` | `sqlite:///./data/codecrafter.db` | Persistence target |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | CORS origin |
| `API_TOKEN` | *(empty)* | Optional shared bearer token |

Requirements: your LLM endpoint must support **tool calling** (OpenAI function-calling format).

---

## Testing

```bash
uv run pytest
```

All agent tests use the deterministic `MockLLMProvider` — **no external inference or API keys required**.

---

## Security

- **Workspace confinement** — path normalization, traversal prevention, symlink escape protection; all operations scoped to the project workspace
- **Docker isolation** (`WORKSPACE_BACKEND=docker`) — commands execute in containers with CPU/memory limits, `no-new-privileges`, and no Docker socket access
- **Command gating** — high-risk patterns blocked as defense-in-depth (not the primary boundary)
- **Git import validation** — only public HTTP/HTTPS URLs; loopback and private addresses rejected
- **Optional auth** — shared bearer token for the whole API

> **Heads up:** Treat agent-generated commands as untrusted. Docker isolation is one security layer, not an absolute sandbox.

---

## License

[MIT](LICENSE)
