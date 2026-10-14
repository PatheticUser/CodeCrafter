# syntax=docker/dockerfile:1.10

# =============================================================================
# CodeCrafter — multi-arch image (linux/amd64 + linux/arm64 / aarch64)
#
# Architecture audit (verified against uv.lock — no x86-only artifacts):
#   - Base images:  ghcr.io/astral-sh/uv, python:3.11-slim-bookworm and
#     caddy:2 (used by docker-compose.yml) all publish arm64 manifests.
#   - Python deps:  fastapi, openai, pydantic-settings, requests, rich,
#     sse-starlette, uvicorn, python-docx are pure Python.
#     pygame (the only compiled wheel) resolves to
#     pygame-2.6.1-cp311-cp311-manylinux_2_17_aarch64...whl on arm64.
#   - No PyTorch, C/C++ extensions, VAD or TTS runtime exists in this
#     repository — nothing to cross-compile.
#
# Build natively on the OCI Ampere A1 (arm64) VM:
#   docker compose --env-file .env.production build
# Build for both architectures from any host (optional):
#   docker buildx build --platform linux/amd64,linux/arm64 -t codecrafter:latest .
# =============================================================================


# ── Stage 1: dependency resolver ─────────────────────────────────────────────
# uv official image (multi-arch) — resolves from uv.lock exactly, no drift.
# uv selects native wheels for the BUILD architecture (aarch64 on Ampere A1),
# so no QEMU emulation and no source compiles.
FROM ghcr.io/astral-sh/uv:0.5-python3.11-bookworm-slim AS deps

WORKDIR /app

# Only copy what uv needs — this layer stays cached on source-only changes.
COPY pyproject.toml uv.lock ./

# Install prod deps into /app/.venv.
# --no-install-project: skip the project itself (source copied in runtime stage).
# --no-dev: dev deps (pytest, ruff) never enter the image.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
# python:3.11-slim-bookworm publishes arm64/v8 images — runs natively on OCI
# Ampere A1 (Oracle Linux/Ubuntu ARM64 hosts need no emulation layer).
FROM python:3.11-slim-bookworm AS runtime

# curl is required by the docker-compose healthcheck (container-local probe).
# Both curl and ca-certificates exist for amd64 and arm64 in Debian bookworm.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Non-root user — container security baseline.
RUN groupadd --gid 1001 appgroup \
 && useradd  --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Virtualenv from deps stage (built for the same architecture).
COPY --from=deps /app/.venv /app/.venv

# Application source only — no tests, no docs, no Landing-Page.
COPY src/       ./src/
COPY functions/ ./functions/
COPY core/      ./core/
COPY ui/        ./ui/
COPY config.py  ./config.py

# Persistent workspace + session storage. docker-compose mounts named volumes
# here; ownership is seeded from this layer (uid 1001) on first start.
RUN mkdir -p /tmp/workspace /tmp/sessions \
 && chown -R appuser:appgroup /tmp/workspace /tmp/sessions

USER appuser

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CODECRAFTER_WORKING_DIR=/tmp/workspace \
    CODECRAFTER_SESSIONS_DIR=/tmp/sessions \
    APP_ENV=production

# Internal port 8000 only — never published on the host; Caddy reverse-proxies
# to it over the dedicated bridge network (see docker-compose.yml).
EXPOSE 8000

# Start command is declared in docker-compose.yml (single source of truth for
# the deployed service); this CMD keeps the image runnable standalone:
#   docker run --rm -p 8000:8000 --env-file .env.production codecrafter:latest
# --proxy-headers: honor X-Forwarded-* from Caddy (real client IP in logs);
# --forwarded-allow-ips=* is safe: port 8000 is reachable only by Caddy on the
# internal bridge network.
CMD ["/app/.venv/bin/uvicorn", \
     "src.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*", \
     "--access-log"]
