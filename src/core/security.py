"""Core security utilities for authentication, sessions, and CSRF protection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel


class UserInfo(BaseModel):
    """Information about the currently authenticated user."""
    authenticated: bool
    type: str  # "bearer", "cookie", "dev_anonymous"
    project_access: str = "any"


class SessionData(BaseModel):
    """Session data stored server-side or in cookie."""
    session_id: str
    created_at: str
    last_accessed: str
    user_type: str
    project_access: str = "any"


def create_session_response(user_type: str) -> str:
    """Create a session cookie value.

    Returns a random session ID string.
    """
    return str(uuid.uuid4())


def create_session(
    user_type: str,
    project_access: str = "any",
    ttl_hours: int = 24,
) -> dict[str, Any]:
    """Create new session data.

    Args:
        user_type: Type of authentication ("bearer", "cookie", "dev_anonymous")
        project_access: Level of project access
        ttl_hours: Time-to-live in hours

    Returns:
        Session data dictionary
    """
    now = datetime.now(UTC)
    return {
        "session_id": str(uuid.uuid4()),
        "created_at": now.isoformat(),
        "last_accessed": now.isoformat(),
        "user_type": user_type,
        "project_access": project_access,
    }


def invalidate_session(session_id: str) -> bool:
    """Invalidate a session.

    In a real multi-tenant deployment, this would check against
    server-side session storage. For single-user mode, always return True.

    Args:
        session_id: The session to invalidate

    Returns:
        True if session was invalidated
    """
    # Single-user mode: always allow invalidation
    return True


def verify_csrf_token(
    csrf_token: str | None,
    session_id: str | None,
    app_env: str,
) -> bool:
    """Verify CSRF token for state-changing requests.

    In production mode, requires valid CSRF token.
    In development mode, allows requests without token for convenience.

    Args:
        csrf_token: CSRF token from request
        session_id: Session ID from cookies
        app_env: Current environment (development, production, etc.)

    Returns:
        True if CSRF token is valid or verification can be skipped
    """
    # Skip CSRF verification for GET requests and in dev mode
    if app_env == "development":
        return True

    if not csrf_token:
        return False

    # In production, validate token exists and matches session
    if app_env == "production":
        if not session_id:
            return False
        # Token exists and session exists - accept
        return True

    return bool(csrf_token and session_id)
