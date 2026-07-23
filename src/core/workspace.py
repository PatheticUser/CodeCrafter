"""Workspace scanning and tree generation."""

import os

from src.core.settings import settings


def scan_workspace_tree(directory=None):
    """Scan workspace and return a compact tree string."""
    if directory is None:
        directory = str(settings.workspace_dir)

    # Directories to skip — junk or build artifacts that bloat the tree
    SKIP_DIRS = {
        "node_modules", "__pycache__", ".venv", "venv", ".git",
        "dist", "build", ".next", "out", "target",
        ".mypy_cache", ".pytest_cache", ".ruff_cache",
    }

    lines = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
        level = os.path.relpath(root, directory)
        if level == ".":
            for f in sorted(files):
                if f.startswith(".") or f.endswith(".pyc") or f == "session.json":
                    continue
                size = os.path.getsize(os.path.join(root, f))
                lines.append(f"{f} ({size:,}B)")
        else:
            indent = "  " * (level.count(os.sep))
            lines.append(f"{indent}{os.path.basename(root)}/")
            for f in sorted(files):
                if f.startswith(".") or f.endswith(".pyc"):
                    continue
                size = os.path.getsize(os.path.join(root, f))
                lines.append(f"{indent}  {f} ({size:,}B)")
    return "\n".join(lines) if lines else "(empty workspace)"
