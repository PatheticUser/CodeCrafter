"""Session management for CodeCrafter."""

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
from ui.display import show_warning, c, Colors, Icons, dim


def generate_session_name():
    """Generate a session name from current timestamp."""
    return datetime.now().strftime(f"{SESSION_PREFIX}{SESSION_TIMESTAMP_FORMAT}")


def _session_path(name):
    """Get the full path for a session file."""
    return os.path.join(SESSIONS_DIR, f"{name}{SESSION_FILE_EXTENSION}")


def get_latest_session_name():
    """Find the most recently modified session file name."""
    pattern = os.path.join(SESSIONS_DIR, f"{SESSION_PREFIX}*{SESSION_FILE_EXTENSION}")
    files = glob.glob(pattern)
    if not files:
        return None
    latest = max(files, key=os.path.getmtime)
    return os.path.splitext(os.path.basename(latest))[0]


def list_sessions():
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


def load_session(session_name=None):
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
        except (json.JSONDecodeError, ValueError):
            # Corrupted session — back it up and start fresh
            backup = path + CORRUPT_EXTENSION
            try:
                os.rename(path, backup)
            except Exception:
                pass
            show_warning(
                f"Session '{session_name}' was corrupted. Backed up and starting fresh."
            )
            return [], generate_session_name()
        except Exception:
            pass
    return [], session_name


def save_session(messages, session_name):
    """Save conversation history to a named session file."""
    try:
        to_save = messages[-MAX_SESSION_MESSAGES:]
        path = _session_path(session_name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def delete_session_file(session_name):
    """Delete a session file. Returns True on success."""
    path = _session_path(session_name)
    if os.path.exists(path):
        try:
            os.remove(path)
            return True
        except Exception:
            return False
    return False


def show_sessions():
    """Display all sessions to the user."""
    sessions = list_sessions()
    if not sessions:
        print(f"  {dim(Icons.INFO)}  No saved sessions found.")
        return
    print()
    print(f"  {c(Icons.BRAIN, Colors.CYAN)}  {c('Saved Sessions', Colors.BOLD)}")
    print(f"  {dim('─' * 52)}")
    for i, s in enumerate(sessions):
        marker = c(Icons.ARROW, Colors.CYAN) if i == 0 else " "
        s_name = s["name"]
        s_mod = s["modified"]
        s_msgs = s["messages"]
        info_line = str(s_mod) + "  |  " + str(s_msgs) + " msgs"
        print(f"  {marker}  {c(s_name, Colors.CYAN)}  {dim(info_line)}")
    print()


class SessionManager:
    """Manages session state and operations."""

    def __init__(self):
        # Ensure sessions directory exists
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        self.messages = []
        self.current_session_name = None
        self._load_or_create()

    def _load_or_create(self):
        """Load existing session or create a new one."""
        self.messages, self.current_session_name = load_session()

    def new_session(self):
        """Start a new session."""
        self.save()
        self.messages = []
        self.current_session_name = generate_session_name()
        return self.current_session_name

    def load(self, session_name):
        """Load a specific session."""
        self.save()
        self.messages, self.current_session_name = load_session(session_name)
        return self.current_session_name, len(self.messages)

    def delete(self, session_name):
        """Delete a session file."""
        return delete_session_file(session_name)

    def save(self):
        """Save current session."""
        if self.current_session_name:
            save_session(self.messages, self.current_session_name)

    def clear(self):
        """Clear current session messages."""
        self.messages = []
        self.save()

    def add_message(self, role, content, **kwargs):
        """Add a message to the session."""
        msg = {"role": role, "content": content}
        msg.update(kwargs)
        self.messages.append(msg)

    def get_messages(self):
        """Get all messages."""
        return self.messages

    def trim_messages(self, keep_first=1, keep_last=6):
        """Trim messages to fit context window."""
        if len(self.messages) > keep_first + keep_last:
            self.messages = self.messages[:keep_first] + self.messages[-keep_last:]
