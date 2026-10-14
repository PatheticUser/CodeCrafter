"""Workspace security and containment utilities."""

from __future__ import annotations

import re
from pathlib import Path


class SecurityError(Exception):
    """Raised when an operation breaches workspace confinement."""

    pass


BLOCKED_COMMAND_PATTERNS = [
    r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?/",
    r"del\s+/[sS]\s+/[qQ]\s+[A-Za-z]:\\",
    r"rmdir\s+/[sS]\s+/[qQ]\s+[A-Za-z]:\\",
    r"format\s+[A-Za-z]:",
    r"mkfs\b",
    r"dd\s+if=",
    r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;",
    r"curl\s+.*-d\s+@",
    r"wget\s+.*--post-file",
    r"shutdown\b",
    r"reboot\b",
    r"reg\s+(delete|add)\s+HKLM",
    r"chmod\s+777\s+/",
    r"chown\s+.*\s+/",
    r"cat\s+.*(\.ssh|\.gnupg|shadow|passwd)",
    r"docker\.sock",
]

_BLOCKED_REGEX = [re.compile(p, re.IGNORECASE) for p in BLOCKED_COMMAND_PATTERNS]


def is_command_blocked(command: str) -> bool:
    """Check if command matches high-risk hostile pattern."""
    return any(p.search(command) for p in _BLOCKED_REGEX)


def resolve_safe_path(root_dir: Path | str, target_path: str, must_exist: bool = False) -> Path:
    """
    Resolve and validate that target_path is strictly within root_dir.
    Resolves symlinks to defend against symlink escapes.
    """
    root_resolved = Path(root_dir).resolve()
    if not root_resolved.is_dir():
        raise SecurityError(f"Workspace root does not exist: {root_resolved}")

    # Remove leading slashes to prevent absolute root overrides
    rel = target_path.strip().lstrip("/\\")
    if not rel:
        candidate = root_resolved
    else:
        candidate = (root_resolved / rel).resolve()

    try:
        # Verify candidate is inside or equal to root_resolved
        candidate.relative_to(root_resolved)
    except ValueError:
        raise SecurityError(
            f"Path traversal detected: '{target_path}' resolves outside workspace boundary "
            f"({root_resolved})"
        )

    if must_exist and not candidate.exists():
        raise FileNotFoundError(f"File or directory not found: '{target_path}'")

    return candidate
