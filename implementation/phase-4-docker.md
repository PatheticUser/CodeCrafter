# Phase 4 — Dockerization

> **Effort:** ~2 days · **Dependencies:** Phase 2  
> **Goal:** Containerize all services for consistent, reproducible deployments. Multi-stage builds for small images, Docker Compose for orchestration.

---

## 4.1 Container Architecture

### What You're Building

Five containers orchestrated by Docker Compose:

- **api** — FastAPI server serving REST + WebSocket endpoints
- **nginx** — reverse proxy handling TLS termination, static file serving, WebSocket upgrade, and security headers
- **postgres** — session and user data persistence
- **redis** — rate limiting backend and response caching
- **ollama** — LLM inference server (optional in compose — may run on host or separate GPU machine)

### Design Principles

- **One concern per container** — the API container doesn't serve static files. Nginx doesn't run Python. Each container does one thing.
- **Stateless API containers** — all state lives in postgres, redis, and the workspace volume. API containers can be killed and recreated without data loss.
- **Named volumes for persistence** — database data, redis data, ollama models, and user workspaces survive container restarts.

---

## 4.2 API Container

### Multi-Stage Build Strategy

Use a two-stage Dockerfile:

**Stage 1 (Builder):**
- Start from `python:3.11-slim`
- Copy the `uv` binary from the official uv image (`ghcr.io/astral-sh/uv:latest`)
- Copy `pyproject.toml` and `uv.lock` FIRST — this is critical for Docker layer caching. Dependencies only re-install when these files change, not on every code edit.
- Run `uv sync --frozen --no-dev` — install production dependencies only, using exact versions from lockfile
- Copy source code and install the project

**Stage 2 (Runtime):**
- Start from `python:3.11-slim` (clean image, no build tools)
- Copy ONLY the virtual environment and source code from stage 1
- Create a non-root user and group for running the application
- Set ownership of workspace and session directories to the non-root user
- Switch to non-root user before the CMD instruction

### Best Practices

- **Layer ordering matters enormously** — dependencies change rarely, code changes often. Copy dependency files before source code. This means Docker caches the expensive `uv sync` layer and only re-runs the cheap source copy on code changes. A well-structured Dockerfile rebuilds in 5 seconds instead of 60.

- **Non-root is non-negotiable** — create a dedicated user (e.g., `codecrafter`) with no login shell. Use `USER codecrafter` before the final `CMD`. Running as root in containers is a security audit failure.

- **Set Python environment variables**:
  - `PYTHONUNBUFFERED=1` — logs appear immediately, not buffered
  - `PYTHONDONTWRITEBYTECODE=1` — don't create `.pyc` files in the container

- **Add a HEALTHCHECK instruction** — Docker uses this to determine container health. Hit `/health` on localhost. Configure 30s interval, 5s timeout, 3 retries, 10s start period (give the app time to boot).

- **Pin base image tags** — use `python:3.11-slim` not `python:latest`. Unpinned tags cause non-reproducible builds.

- **Target final image size under 300MB** — the multi-stage build should strip build dependencies (gcc, pip cache, etc.) from the runtime image.

---

## 4.3 Frontend Container

### Build Strategy

Also two-stage:

**Stage 1 (Build):**
- Start from `node:20-alpine`
- Copy `package.json` and `package-lock.json` first (layer caching)
- Run `npm ci` (clean install, faster and more reproducible than `npm install`)
- Copy source code
- Pass build-time environment variables via `ARG` (API URL, WS URL)
- Run `npm run build` — produces static `dist/` directory

**Stage 2 (Serve):**
- Start from `nginx:alpine`
- Remove default nginx config
- Copy custom nginx config for SPA routing (all paths → `index.html`)
- Copy `dist/` from build stage to nginx's HTML directory
- Result: tiny image (~30MB) serving optimized static files

### Best Practices

- **Use `npm ci` not `npm install`** — `ci` uses the lockfile exactly, is faster, and deletes `node_modules` before installing. This is the correct command for CI/CD and Docker builds.

- **Build-time variables via ARG, not ENV** — `ARG` values are only available during build. Don't bake runtime secrets into the image.

- **SPA routing in nginx** — configure `try_files $uri $uri/ /index.html` so that client-side routes (e.g., `/chat`, `/login`) work on page refresh instead of returning 404.

---

## 4.4 Nginx Reverse Proxy

### What To Configure

Nginx sits in front of everything, handling:

1. **Static file serving** — frontend assets with aggressive caching (30 day expiry, `immutable` flag for hashed filenames)

2. **API proxying** — forward `/api/*` and `/auth/*` to the API container on port 8000. Set proper headers: `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`. Increase `proxy_read_timeout` to 120s — agent turns can be slow.

3. **WebSocket upgrade** — the `/api/v1/chat/stream` path needs special handling. Set `proxy_http_version 1.1`, `Upgrade` and `Connection` headers. Set read/send timeouts to 3600s (1 hour) to keep long-lived connections alive.

4. **Security headers** — add to every response:
   - `X-Frame-Options: DENY` — prevent clickjacking
   - `X-Content-Type-Options: nosniff` — prevent MIME sniffing
   - `X-XSS-Protection: 1; mode=block` — legacy XSS filter
   - `Referrer-Policy: strict-origin-when-cross-origin` — control referer leakage
   - `Content-Security-Policy` — restrict script/style/font sources

5. **Health check passthrough** — `/health` proxied to API without auth.

6. **Block sensitive paths** — deny access to `/.env`, `/.git`, and any dotfile.

### Best Practices

- **Gzip compression** — enable `gzip on` for text, CSS, JS, JSON, SVG. Don't compress images (already compressed). Typical 60-80% size reduction.

- **Rate limiting at nginx level** — add a basic `limit_req_zone` as a first line of defense before requests even reach the API. This protects against DDoS.

- **Access logging** — log in a structured format (JSON) for easier parsing. Include request duration, upstream response time, and client IP.

- **Separate server blocks for API and frontend** — even if they're on the same domain, use distinct location blocks. This makes it easy to split them to separate domains later.

---

## 4.5 Docker Compose — Development

### What To Configure

Create `docker-compose.yml` for local development with:

1. **Service definitions** — api, postgres, redis, ollama, nginx. Each with proper environment variables, health checks, and dependency ordering.

2. **Environment variables** — set in the compose file, overriding `.env` where needed:
   - API connects to `http://ollama:11434/v1` (container-to-container via Docker network)
   - Database URL uses compose service name: `postgresql+asyncpg://user:pass@postgres:5432/db`
   - Redis URL: `redis://redis:6379/0`

3. **Health check dependencies** — API depends on postgres and redis being healthy (not just started). Use `depends_on` with `condition: service_healthy`. This prevents the API from crashing on startup because the database isn't ready yet.

4. **Volumes**:
   - `pgdata` — persists database across restarts
   - `redisdata` — persists redis across restarts
   - `ollama_models` — persists downloaded LLM models (these are gigabytes, you don't want to re-download them)
   - `workspaces` — persists user workspaces
   - Bind mount `./src` into the API container for hot reload during development (read-only)

5. **Port mappings** — expose nginx on 80, postgres on 5432, redis on 6379 for local debugging tools.

6. **GPU support for Ollama** — add commented-out deploy section for NVIDIA GPU passthrough. Uncomment when running on a GPU-equipped machine.

### Best Practices

- **Use `restart: unless-stopped`** in dev — containers restart on crash but not when you explicitly stop them.

- **Don't hardcode passwords in compose** — use `.env` file variables. Even for dev, practice good habits.

- **Resource limits in dev too** — add memory limits to prevent a runaway container from eating all your RAM. 1GB for API, 512MB for postgres, 256MB for redis.

---

## 4.6 Docker Compose — Production Override

### What To Do

Create `docker-compose.prod.yml` as a production override file. Use with: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

Production differences:

1. **No source code bind mounts** — images contain everything needed. No hot reload.
2. **Replica count** — run 2+ API instances behind nginx for redundancy.
3. **Stricter resource limits** — enforce CPU and memory limits.
4. **Real passwords** — from environment variables, not hardcoded defaults.
5. **TLS volumes** — mount Let's Encrypt certificate directory into nginx.
6. **`restart: always`** — always restart, even after system reboot.
7. **No port exposure for internal services** — postgres and redis are only accessible from the Docker network, not from the host.

### Best Practices

- **Never use `latest` tags in production** — pin image versions (`postgres:16-alpine`, `redis:7-alpine`, `nginx:1.27-alpine`).
- **Use `docker compose pull` before `up`** — ensure you're running the latest built images, not cached old ones.
- **Separate networks** — create a `frontend` network (nginx ↔ api) and a `backend` network (api ↔ postgres ↔ redis). This prevents nginx from directly accessing the database.

---

## 4.7 .dockerignore

### What To Exclude

Create a `.dockerignore` that mirrors `.gitignore` plus Docker-specific exclusions:

- `.git/` — massive, not needed in containers
- `.venv/` — rebuilt inside the container
- `__pycache__/`, `*.pyc` — rebuilt by Python
- `.env` — secrets must not be baked into images
- `sessions/`, `workspace/`, `workspaces/` — runtime data, not build artifacts
- `node_modules/` — rebuilt by `npm ci`
- `frontend/dist/` — rebuilt inside the frontend build stage
- `tests/`, `implementation/` — not needed in production
- `*.md` except README — documentation isn't runtime-required

### Why It Matters
A bad `.dockerignore` can increase build time from 5 seconds to 5 minutes by copying gigabytes of unnecessary files into the build context.

---

## 4.8 Makefile

### What To Include

Create a `Makefile` with common operations as targets. This is the single command reference for all developers:

- **`make dev`** — `docker compose up --build` (build and start everything)
- **`make prod`** — compose up with production override
- **`make build`** — build images without starting
- **`make test`** — run pytest with coverage
- **`make logs`** — tail all container logs
- **`make logs-api`** — tail only API logs
- **`make db-migrate`** — run Alembic migrations
- **`make db-rollback`** — rollback last migration
- **`make clean`** — tear down everything including volumes
- **`make shell`** — open a bash shell in the API container

### Best Practices
- **Document each target** — add comments or a `make help` target that prints available commands.
- **Use `.PHONY`** — declare all targets as phony to prevent conflicts with actual files named `build`, `test`, etc.
- **Pin to the correct compose files** — prod targets always include both base and override files.

---

## Phase 4 Final Checklist

- [ ] `docker compose up --build` starts all 5 services without errors
- [ ] API reachable at `http://localhost/api/v1/chat` through nginx
- [ ] Frontend served at `http://localhost/` through nginx
- [ ] WebSocket works through nginx reverse proxy (upgrade headers correct)
- [ ] `curl http://localhost/health` returns `{"status": "ok"}`
- [ ] API container runs as non-root user (verify with `docker compose exec api whoami`)
- [ ] API image size < 300MB (`docker images` to check)
- [ ] Data persists across `docker compose down && docker compose up`
- [ ] `.dockerignore` excludes dev files (verify with `docker compose build` speed)
- [ ] `make dev` and `make prod` both work correctly
- [ ] No secrets baked into any Docker image
