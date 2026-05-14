# CodeCrafter — Production Implementation Plan

> **Status:** Draft v1 · **Created:** 2026-05-14
> **Goal:** Transform CodeCrafter from local CLI tool → production-grade SaaS with inference API, web frontend, Docker deployment, and full observability.

---

## Current State Analysis

```
CodeCrafter/
├── main.py              # 564-line monolith: CLI loop + agent logic
├── config.py            # Flat config, hardcoded values, no env-var support
├── core/
│   ├── api_manager.py   # Ollama client, model fallback (OpenAI SDK)
│   └── workspace.py     # Simple os.walk tree scanner
├── ui/                  # ANSI terminal display (display.py + spinner.py)
├── chat_session/        # JSON file-based session persistence
├── functions/           # 9 tool implementations (run_code, write_file, etc.)
├── services/            # Empty — unused
├── commands/            # Empty — unused
├── tools/               # Empty — unused
└── workspace/           # Sandboxed user file directory
```

### Critical Gaps

| Area | Current | Target |
|------|---------|--------|
| API | None — CLI only | FastAPI REST + WebSocket |
| Frontend | Terminal ANSI UI | Web UI per DESIGN.md (cream/coral editorial) |
| Auth | None | JWT + API keys |
| Config | Hardcoded `config.py` | Pydantic Settings + `.env` |
| Sessions | JSON files on disk | PostgreSQL / Redis |
| Docker | None | Multi-stage build + Compose |
| CI/CD | None | GitHub Actions pipeline |
| Monitoring | None | Structured logging + Prometheus + Sentry |
| Testing | None | pytest + Playwright |
| Security | Basic path traversal + cmd blocklist | Full sandboxing + rate limiting |

---

## Target Architecture

```
                    ┌─────────────────────────────────────┐
                    │          Client Layer                │
                    │  ┌──────────┐    ┌──────────────┐   │
                    │  │ Web UI   │    │ CLI Client   │   │
                    │  │ (React)  │    │ (main.py)    │   │
                    │  └────┬─────┘    └──────┬───────┘   │
                    └───────┼─────────────────┼───────────┘
                            │                 │
                    ┌───────▼─────────────────▼───────────┐
                    │       Nginx Reverse Proxy            │
                    └───────────────┬──────────────────────┘
                                    │
                    ┌───────────────▼──────────────────────┐
                    │       FastAPI Server                  │
                    │  ┌─────────┐  ┌──────────────────┐   │
                    │  │ REST    │  │ WebSocket Handler │   │
                    │  │ Routes  │  │ (streaming)       │   │
                    │  └────┬────┘  └────────┬──────────┘   │
                    └───────┼────────────────┼─────────────┘
                            │                │
                    ┌───────▼────────────────▼─────────────┐
                    │       Core Engine                     │
                    │  ┌────────┐ ┌───────┐ ┌──────────┐   │
                    │  │ Agent  │ │ Tools │ │ Sandbox  │   │
                    │  │ Loop   │ │ 9 fns │ │ Manager  │   │
                    │  └───┬────┘ └───────┘ └──────────┘   │
                    └──────┼───────────────────────────────┘
                           │
          ┌────────────────┼────────────────────┐
          │                │                    │
    ┌─────▼────┐    ┌──────▼─────┐     ┌────────▼───┐
    │ Ollama   │    │ PostgreSQL │     │   Redis    │
    │ (LLM)   │    │ (sessions) │     │ (cache)    │
    └──────────┘    └────────────┘     └────────────┘
```

---

## Phase Overview

| # | Phase | File | Effort | Dependencies |
|---|-------|------|--------|-------------|
| 1 | Codebase Hardening | `phase-1-hardening.md` | ~3 days | None |
| 2 | Inference API | `phase-2-api.md` | ~4 days | Phase 1 |
| 3 | Frontend | `phase-3-frontend.md` | ~5 days | Phase 2 |
| 4 | Dockerization | `phase-4-docker.md` | ~2 days | Phase 2 |
| 5 | CI/CD Pipeline | `phase-5-cicd.md` | ~2 days | Phase 4 |
| 6 | Deployment | `phase-6-deployment.md` | ~2 days | Phase 4,5 |
| 7 | Observability | `phase-7-observability.md` | ~2 days | Phase 6 |

**Total estimated effort: ~20 days**

```
Phase 1 (Hardening) ──► Phase 2 (API) ──► Phase 3 (Frontend)
                                │
                                ├──► Phase 4 (Docker) ──► Phase 5 (CI/CD)
                                │                              │
                                └──────────────────────────────┼──► Phase 6 (Deploy)
                                                                        │
                                                               Phase 7 (Observability)
```

---

## Conventions

- **Package manager:** `uv` only (no pip/conda)
- **Python:** 3.11+, type hints everywhere
- **Linting:** `ruff` for lint + format
- **Testing:** `pytest` + `pytest-asyncio`
- **Frontend:** Vite + React + vanilla CSS (DESIGN.md tokens)
- **Containers:** rootless, non-root user, multi-stage
- **Secrets:** `.env` files, never committed

**IMPORTANT:** Read each phase file in order. Each builds on previous and includes specific file paths, code patterns, and acceptance criteria.
