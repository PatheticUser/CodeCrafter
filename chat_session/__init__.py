"""Chat session management for CodeCrafter.

This module manages conversation sessions (stored in the 'sessions/' directory).
"""

from .manager import (
    SessionManager,
    generate_session_name,
    get_latest_session_name,
    list_sessions,
    load_session,
    save_session,
    delete_session_file,
)

__all__ = [
    "SessionManager",
    "generate_session_name",
    "get_latest_session_name",
    "list_sessions",
    "load_session",
    "save_session",
    "delete_session_file",
]
