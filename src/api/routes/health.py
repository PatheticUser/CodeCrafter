"""Health check routes."""

from fastapi import APIRouter

from src.core.settings import settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check():
    """Health check endpoint reporting API and configuration readiness."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "workspace_backend": settings.WORKSPACE_BACKEND,
        "llm_configured": bool(settings.LLM_BASE_URL),
        "model": settings.LLM_MODEL,
    }
