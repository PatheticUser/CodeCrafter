"""Session management for CodeCrafter.

Handles conversation persistence with proper error logging instead of
silent exception swallowing.
"""

import json
import glob
import os
from datetime import datetime

from config import (
    SESSIONS_DIR,
    MAX_SESSION_MESSAGES,
    SESSION_FILE_EXTENSION,
    CORRUPT_EXTENSION,
    SESSION_PREFIX,
    SESSION_TIMESTAMP_FORMAT,
)
from services.logger import logger


def generate_session_name() -> str:
    """Generate a session name from current timestamp."""
    return datetime.now().strftime(f"{SESSION_PREFIX}{SESSION_TIMESTAMP_FORMAT}")


def _session_path(name: str) -> str:
    """Get the full path for a session file."""
    return os.path.join(SESSIONS_DIR, f"{name}{SESSION_FILE_EXTENSION}")


def get_latest_session_name() -> str | None:
    """Find the most recently modified session file name."""
    pattern = os.path.join(SESSIONS_DIR, f"{SESSION_PREFIX}*{SESSION_FILE_EXTENSION}")
    files = glob.glob(pattern)
    if not files:
        return None
    latest = max(files, key=os.path.getmtime)
    return os.path.splitext(os.path.basename(latest))[0]


def list_sessions() -> list[dict]:
    """List all sessions with timestamps and message counts."""
    pattern = os.path.join(SESSIONS_DIR, f"{SESSION_PREFIX}*{SESSION_FILE_EXTENSION}")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    sessions = []
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        mtime = datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M")
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            msg_count = len(data) if isinstance(data, list) else 0
        except Exception:
            msg_count = "?"
        sessions.append({"name": name, "modified": mtime, "messages": msg_count})
    return sessions


def load_session(session_name: str | None = None) -> tuple[list, str]:
    """Load conversation history from a named session."""
    if session_name is None:
        session_name = get_latest_session_name()
    if session_name is None:
        return [], generate_session_name()

    path = _session_path(session_name)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data[-MAX_SESSION_MESSAGES:], session_name
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Session '%s' is corrupted: %s. Backing up.", session_name, e)
            backup = path + CORRUPT_EXTENSION
            try:
                os.rename(path, backup)
            except Exception as rename_err:
                logger.error("Failed to backup corrupt session: %s", rename_err)
            return [], generate_session_name()
        except Exception as e:
            logger.error("Failed to load session '%s': %s", session_name, e, exc_info=True)
    return [], session_name


def save_session(messages: list, session_name: str) -> None:
    """Save conversation history to a named session file."""
    try:
        to_save = messages[-MAX_SESSION_MESSAGES:]
        path = _session_path(session_name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(
            "Failed to save session '%s' (%d messages): %s",
            session_name, len(messages), e, exc_info=True,
        )


def delete_session_file(session_name: str) -> bool:
    """Delete a session file. Returns True on success."""
    path = _session_path(session_name)
    if os.path.exists(path):
        try:
            os.remove(path)
            return True
        except Exception as e:
            logger.error("Failed to delete session '%s': %s", session_name, e)
            return False
    return False


class SessionManager:
    """Manages session state and operations."""

    def __init__(self) -> None:
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        self.messages: list[dict] = []
        self.current_session_name: str | None = None
        self._load_or_create()

    def _load_or_create(self) -> None:
        self.messages, self.current_session_name = load_session()

    def new_session(self) -> str:
        self.save()
        self.messages = []
        self.current_session_name = generate_session_name()
        return self.current_session_name

    def load(self, session_name: str) -> tuple[str, int]:
        self.save()
        self.messages, self.current_session_name = load_session(session_name)
        return self.current_session_name, len(self.messages)

    def save(self) -> None:
        if self.current_session_name:
            save_session(self.messages, self.current_session_name)

    def clear(self) -> None:
        self.messages = []
        self.save()

    def add_message(self, role: str, content: str = "", **kwargs) -> None:
        msg = {"role": role, "content": content}
        msg.update(kwargs)
        self.messages.append(msg)

    def get_messages(self) -> list[dict]:
        return self.messages

    def trim_messages(self, keep_first: int = 1, keep_last: int = 6) -> None:
        if len(self.messages) > keep_first + keep_last:
            self.messages = self.messages[:keep_first] + self.messages[-keep_last:]
            logger.info(
                "Trimmed session to %d messages (kept first %d + last %d)",
                len(self.messages), keep_first, keep_last,
            )
