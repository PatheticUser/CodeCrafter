# Phase 2 — Inference API

> **Effort:** ~4 days · **Dependencies:** Phase 1  
> **Goal:** Expose CodeCrafter's agent loop via a production-grade FastAPI server with REST and WebSocket endpoints, authentication, rate limiting, and per-user workspace isolation.

---

## 2.1 Dependency Selection

### What To Install

- **FastAPI** — async-native, automatic OpenAPI docs, Pydantic integration. The standard for Python APIs in 2026.
- **Uvicorn** with `standard` extras — ASGI server with HTTP/2, WebSocket, and `uvloop` for performance.
- **python-jose** with cryptography backend — JWT token creation and verification. Prefer over PyJWT for its broader algorithm support.
- **passlib** with bcrypt backend — password hashing. Never roll your own.
- **SQLAlchemy** with async driver — ORM for users and sessions. Use `aiosqlite` for dev, `asyncpg` for prod (PostgreSQL).
- **Alembic** — database migration management. Never modify production schemas by hand.
- **Redis client** (`redis[hiredis]`) — for rate limiting and response caching.
- **SlowAPI** — rate limiting middleware built on top of `limits` library.
- **python-multipart** — required by FastAPI for form data parsing (auth endpoints).

### Best Practices
- **Pin major versions** in `pyproject.toml`, let `uv.lock` handle exact pins.
- **Separate dev dependencies** — testing and linting tools go under `[tool.uv.dev-dependencies]`, never in production deps.
- **Audit new dependencies** — check GitHub stars, last commit date, known CVEs before adding anything.

---

## 2.2 API Architecture

### Module Organization

Create `src/api/` with clear separation of concerns:

- **`app.py`** — FastAPI application factory. Creates the app, attaches middleware, includes routers. Uses the lifespan pattern (not deprecated `on_event`) for startup/shutdown.
- **`deps.py`** — Dependency injection functions. Database sessions, current user extraction, rate limiter access. FastAPI's `Depends()` system keeps routes clean.
- **`middleware.py`** — Request ID generation, request timing, CORS configuration. Middleware order matters: last added is first executed.
- **`routes/`** — one file per resource: health, auth, chat, sessions, workspace, models.
- **`schemas/`** — Pydantic models for request/response validation. Separate from database models.
- **`models/`** — SQLAlchemy ORM models for database tables.
- **`security/`** — JWT handling, password hashing, rate limiting configuration.

### Design Principles

- **Routes are thin** — a route function should validate input, call a service/agent, format output. No business logic in routes.
- **The agent loop is NOT in the API layer** — routes call `AgentLoop.run_turn()` from `src/core/agent.py`. The API is a transport layer, not the brain.
- **Every endpoint returns structured responses** — Pydantic response models enforce consistency. No raw dicts.
- **Versioned API prefix** — all endpoints under `/api/v1/`. This allows breaking changes in future `/api/v2/` without disrupting existing clients.

---

## 2.3 Application Factory

### What To Do

1. **Create the FastAPI app using a factory function** — `create_app() -> FastAPI`. This pattern allows creating separate app instances for testing.

2. **Use the `lifespan` context manager** — this is the modern replacement for `@app.on_event("startup")`. In the startup phase:
   - Verify Ollama connectivity (fail fast if unreachable)
   - Initialize database connection pool
   - Run any pending Alembic migrations (optional, safer to do manually)
   - Warm up the model list cache

3. **Attach middleware in correct order**:
   - Timing middleware (outermost — captures total request time)
   - Request ID middleware (generates UUID, adds to response headers)
   - CORS middleware (configured per environment)

4. **Register routers with prefixes** — health routes at root (`/health`, `/ready`), auth at `/auth/`, everything else at `/api/v1/`.

5. **Conditional docs** — expose `/docs` and `/redoc` only when `settings.debug` is True. Production APIs should not expose interactive documentation publicly.

### Best Practices
- **One `create_app()` function, one `app = create_app()` at module level** — Uvicorn imports the module-level `app` object. Tests create their own via `create_app()`.
- **CORS origins must be explicit in production** — never use `allow_origins=["*"]` in prod. Whitelist your frontend domain only.
- **Set reasonable request body limits** — FastAPI defaults are generous. For chat messages, enforce max 10KB. For file uploads, max 5MB.

---

## 2.4 Request/Response Schemas

### What To Define

**Chat schemas:**
- `ChatRequest` — message (string, min 1 char, max 10K chars), optional session_id, optional model override
- `ChatResponse` — response text, session_id, list of tool calls (name + args + result), token usage dict, model_used string
- `StreamChunk` — event type enum (tool_start, tool_result, text_delta, text_done, error, done) + data dict

**Auth schemas:**
- `UserCreate` — email (validated), password (min 8 chars, must contain number + letter)
- `UserLogin` — email, password
- `TokenResponse` — access_token string, token_type ("bearer"), expires_in seconds

**Session schemas:**
- `SessionCreate` — optional name string
- `SessionResponse` — id, name, message_count, model, created_at, updated_at
- `SessionList` — list of SessionResponse

**Workspace schemas:**
- `FileInfo` — path, size_bytes, is_directory, children_count
- `FileContent` — path, content, line_count

### Best Practices
- **Use Pydantic's `Field()` for validation** — min/max length, regex patterns, examples for docs.
- **Response models should never expose internal fields** — no database IDs, no hashed passwords, no internal error traces.
- **Use enums for fixed value sets** — stream event types, model names, error codes.
- **Add `model_config` with `json_schema_extra`** — provides examples in the auto-generated OpenAPI docs. This dramatically improves API usability.

---

## 2.5 Chat Endpoint (REST)

### Endpoint: `POST /api/v1/chat`

This is the core inference endpoint. It receives a user message, runs the full agent loop, and returns the final response.

### What To Do

1. **Accept `ChatRequest`** — validate message length, extract optional session_id and model override.

2. **Authenticate the request** — extract JWT from `Authorization: Bearer <token>` header. Use FastAPI's `Depends(get_current_user)` pattern. Return 401 if invalid/expired.

3. **Rate limit check** — enforce per-user limits (default 30 requests/minute). Return 429 with `Retry-After` header if exceeded.

4. **Load or create session** — if `session_id` provided, load from database (verify it belongs to the authenticated user). If not provided, create a new session.

5. **Scope workspace** — each user gets their own workspace directory: `workspaces/{user_id}/`. Create on first use. All tool operations are confined to this directory.

6. **Run the agent** — instantiate `AgentLoop`, call `run_turn(session.messages, workspace_path)`. This may take 5-60 seconds depending on tool calls.

7. **Return structured response** — extract final text, tool call history, token usage from the agent's response list.

8. **Save session** — persist updated messages to database.

### Best Practices
- **Set a timeout** — agent turns can hang if Ollama is slow. Use `asyncio.wait_for()` with a 120-second timeout. Return 504 Gateway Timeout if exceeded.
- **Don't expose raw errors** — catch exceptions, log the full traceback server-side, return a sanitized error message to the client.
- **Include `X-Request-ID` in responses** — makes debugging trivial. Client reports a problem → grep logs by request ID.
- **Return `model_used` in response** — if fallback occurred, the client should know which model actually answered.

---

## 2.6 WebSocket Streaming Endpoint

### Endpoint: `WebSocket /api/v1/chat/stream`

Real-time streaming of agent responses. Each tool call and text chunk is sent as a separate WebSocket message.

### What To Do

1. **Define a WebSocket protocol**:
   - Client sends: JSON with `message`, `session_id`, `token` fields
   - Server streams: JSON with `event` (enum) and `data` (dict) fields
   - Events: `tool_start` → `tool_result` → `text_delta` (may repeat) → `done`
   - Error events sent as `{"event": "error", "data": {"detail": "..."}}`

2. **Authenticate on first message** — WebSocket doesn't support HTTP headers in all browsers. Accept the JWT token in the first message payload. Reject and close if invalid.

3. **Use the streaming variant of agent loop** — `AgentLoop` should support a generator/async generator mode where it yields each step. Each yield becomes a WebSocket `send_json()`.

4. **Handle disconnections gracefully** — wrap the handler in try/except for `WebSocketDisconnect`. Clean up any in-progress tool executions.

5. **Implement heartbeat** — send a ping every 30 seconds to detect dead connections. Nginx and load balancers may close idle WebSockets.

### Best Practices
- **Don't stream raw LLM output** — CodeCrafter's agent uses tool calling, not free-text streaming. Stream structured events (tool started, tool finished, final text), not token-by-token text.
- **Buffer text deltas** — if the agent produces a long response, batch it into reasonable chunks (e.g., every 100 characters or every sentence) rather than character-by-character.
- **Track active connections** — maintain a counter of active WebSocket connections for monitoring (Phase 7 metrics).
- **Set connection limits** — max 5 concurrent WebSocket connections per user to prevent resource exhaustion.

---

## 2.7 Authentication System

### What To Build

Three endpoints: register, login, refresh.

### Registration Flow
1. Accept email + password
2. Validate email format, password strength (min 8 chars, at least one letter and one number)
3. Check email uniqueness in database
4. Hash password with bcrypt (cost factor 12 — balances security vs. performance)
5. Create user record in database
6. Return JWT access token

### Login Flow
1. Accept email + password
2. Look up user by email
3. Verify password against stored hash
4. Return JWT access token with user_id in claims

### Token Refresh
1. Accept valid (non-expired) token via `Authorization` header
2. Issue a new token with fresh expiration
3. This allows clients to stay logged in without re-entering credentials

### JWT Design Decisions
- **Algorithm: HS256** — symmetric, fast, sufficient for single-server deployments. Switch to RS256 if you ever need to verify tokens on multiple services without sharing secrets.
- **Expiration: 60 minutes** — short enough to limit damage from stolen tokens, long enough to not annoy users. Pair with refresh endpoint.
- **Claims:** `sub` (user_id), `exp` (expiration), `iat` (issued at). Don't put sensitive data in claims — JWTs are base64-encoded, not encrypted.
- **Secret key: minimum 32 bytes** — generate with `openssl rand -hex 32`. Store in `.env`, never in code.

### Best Practices
- **Never store plaintext passwords** — this should be obvious but must be stated. bcrypt with cost 12.
- **Rate limit auth endpoints aggressively** — 5 attempts per minute per IP to prevent brute force.
- **Don't reveal whether an email exists** — on failed login, return "Invalid credentials" not "User not found" vs "Wrong password".
- **Log all auth events** — successful logins, failed attempts, token refreshes. Include IP address for audit trails.

---

## 2.8 Rate Limiting

### What To Do

1. **Use SlowAPI** — it integrates directly with FastAPI and uses Redis as a backend for distributed rate limiting.

2. **Define rate tiers**:
   - Chat endpoints: 30 requests/minute per user
   - Auth endpoints: 5 requests/minute per IP (prevent brute force)
   - Workspace file operations: 60 requests/minute per user
   - Health checks: unlimited (monitoring needs these)

3. **Return proper headers** — `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`. Clients need these to implement backoff.

4. **Return 429 Too Many Requests** — with `Retry-After` header indicating when the client can retry.

### Best Practices
- **Rate limit by user ID, not just IP** — IP-based limiting breaks for users behind corporate NAT. Use the authenticated user ID as the primary key.
- **Use Redis as backend** — in-memory rate limiting doesn't work with multiple API workers. Redis provides shared state.
- **Don't rate limit internal health checks** — your monitoring system shouldn't trigger rate limits.
- **Log rate limit events** — know which users are hitting limits and whether limits need adjustment.

---

## 2.9 Per-User Workspace Isolation

### What To Do

1. **Create a workspace directory per user** — `workspaces/{user_id}/`. Created lazily on first API request.

2. **All tool operations scoped to user workspace** — when the agent calls `run_code` or `write_file`, the `working_directory` parameter is set to the user's workspace. The existing path traversal protections in each tool prevent escaping.

3. **Enforce resource limits**:
   - Maximum workspace size: 50MB per user
   - Maximum file count: 500 files per workspace
   - Maximum single file size: 5MB
   - Check these limits before any write operation

4. **Workspace cleanup policy** — workspaces inactive for 30+ days can be archived or deleted. Notify users via email before deletion.

### Best Practices
- **Never trust user-provided paths** — even with path traversal checks, validate that the resolved path is within the user's workspace.
- **Use UUIDs for user workspace directories** — don't use email addresses or usernames in paths. They can contain special characters and change over time.
- **Log all file operations** — who created/modified/deleted what, when. Useful for abuse detection and debugging.

---

## 2.10 Database Setup

### What To Do

1. **Define SQLAlchemy models** for `User` and `ChatSession` tables:
   - User: id (UUID), email (unique, indexed), hashed_password, is_active, created_at
   - ChatSession: id (UUID), user_id (FK, indexed), name, messages (JSON), model, created_at, updated_at

2. **Use async SQLAlchemy** — FastAPI is async, your database layer should be too. Use `create_async_engine` and `AsyncSession`.

3. **Set up Alembic** for migrations:
   - `uv run alembic init alembic`
   - Configure `alembic.ini` to read `DATABASE_URL` from settings
   - Create initial migration: `uv run alembic revision --autogenerate -m "initial tables"`
   - Apply: `uv run alembic upgrade head`

4. **Use SQLite for development, PostgreSQL for production** — `aiosqlite` for dev (zero setup), `asyncpg` for prod (performance, concurrency). The `DATABASE_URL` in `.env` controls which is used.

### Best Practices
- **Always use migrations** — never modify production schemas manually. Every change goes through Alembic.
- **Index foreign keys** — `user_id` on `chat_sessions` must be indexed. SQLAlchemy doesn't do this automatically.
- **Use UTC timestamps** — `datetime.now(timezone.utc)`, never `datetime.now()`. Timezone-naive timestamps cause subtle bugs.
- **Connection pooling** — set pool size to 20, max overflow to 10 for production. Monitor pool exhaustion.
- **JSON column for messages** — storing the message history as a JSON column is pragmatic for now. If you need to query individual messages later, normalize into a separate table.

---

## 2.11 Health Endpoints

### What To Build

Two endpoints serving different purposes:

**`GET /health`** — Liveness probe. "Is the process alive?" Returns 200 with `{"status": "ok"}`. Should never fail unless the process is dead. Used by Docker `HEALTHCHECK` and load balancers.

**`GET /ready`** — Readiness probe. "Can we serve traffic?" Checks:
- Ollama reachable (can list models)
- Database connection works (run a simple query)
- Redis connection works (ping)

Returns `{"status": "ok", "checks": {...}}` if all pass, `{"status": "degraded", ...}` if any fail. Kubernetes/Docker uses this to decide whether to route traffic to this instance.

### Best Practices
- **Health checks must be fast** — timeout each sub-check at 2 seconds. A slow health check cascades into deployment failures.
- **No authentication on health endpoints** — monitoring systems and load balancers need unauthenticated access.
- **Don't check external APIs in liveness** — liveness only checks "is the process healthy?" Dependency checks go in readiness.

---

## 2.12 Running & Testing the API

### Development
- Run with `uv run uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000`
- `--reload` watches for file changes and restarts automatically
- OpenAPI docs available at `http://localhost:8000/docs`

### Production
- Run with `uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --workers 4`
- Worker count = 2 × CPU cores + 1 (general guideline)
- No `--reload` in production

### API Testing Strategy
- Test each route independently using `httpx.AsyncClient` with FastAPI's `TestClient`
- Use a test database (separate SQLite file)
- Mock the Ollama client — don't call real LLMs in CI
- Test auth flows end-to-end: register → login → use token → expire → refresh
- Test rate limiting by sending bursts of requests
- Test WebSocket protocol with `websockets` test client

---

## Phase 2 Final Checklist

- [ ] `POST /api/v1/chat` returns valid agent response with tool call history
- [ ] WebSocket `/api/v1/chat/stream` streams events in real-time
- [ ] JWT auth works: register → login → access protected endpoint → refresh
- [ ] Rate limiting returns 429 with proper headers
- [ ] Each user has isolated workspace directory
- [ ] Health endpoints return correct status
- [ ] OpenAPI docs visible at `/docs` in dev, hidden in prod
- [ ] Database migrations run cleanly: `uv run alembic upgrade head`
- [ ] All API routes have tests
- [ ] CLI still works alongside the API (both use same `AgentLoop`)
