"""FastAPI application for CodeCrafter."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import agent_router, health_router, projects_router, sessions_router
from src.core.settings import settings
from src.workspace.manager import workspace_manager

logger = logging.getLogger("codecrafter.api")


def verify_api_token(authorization: str | None = Header(None)) -> None:
    """Optional Bearer token authentication."""
    if not settings.API_TOKEN:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authorization header",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication token",
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager handling startup initialization and shutdown cleanup."""
    logger.info("Starting %s v%s...", settings.APP_NAME, settings.APP_VERSION)
    settings.workspace_root_dir.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("Shutting down %s, cleaning up container workspaces...", settings.APP_NAME)
    await workspace_manager.cleanup_all()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Browser-accessible cloud-ready AI coding assistant environment.",
    lifespan=lifespan,
    dependencies=[Depends(verify_api_token)] if settings.API_TOKEN else [],
)

# CORS configuration
allowed_origins = list(set(settings.CORS_ORIGINS + [settings.FRONTEND_ORIGIN]))
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router)
app.include_router(projects_router)
app.include_router(sessions_router)
app.include_router(agent_router)
