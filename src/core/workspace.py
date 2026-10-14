"""Workspace scanning and tree generation."""

import os

from src.core.settings import settings


def scan_workspace_tree(directory=None):
    """Scan workspace and return a compact tree string.

    Caps output to prevent context overflow.
    Shows total file count when truncated.
    """
    if directory is None:
        directory = str(settings.workspace_dir)

    # Directories to skip — junk or build artifacts that bloat the tree
    skip_dirs = {
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".git",
        "dist",
        "build",
        ".next",
        "out",
        "target",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "site-packages",
        ".cache",
        ".npm",
    }

    max_items = settings.MAX_TREE_ITEMS
    lines = []
    total_files = 0
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in skip_dirs]
        level = os.path.relpath(root, directory)
        if level == ".":
            for f in sorted(files):
                if f.startswith(".") or f.endswith(".pyc") or f == "session.json":
                    continue
                total_files += 1
                if len(lines) < max_items:
                    size = os.path.getsize(os.path.join(root, f))
                    lines.append(f"{f} ({size:,}B)")
        else:
            indent = "  " * (level.count(os.sep))
            dir_label = f"{indent}{os.path.basename(root)}/"
            if len(lines) < max_items:
                lines.append(dir_label)
            for f in sorted(files):
                if f.startswith(".") or f.endswith(".pyc"):
                    continue
                total_files += 1
                if len(lines) < max_items:
                    size = os.path.getsize(os.path.join(root, f))
                    lines.append(f"{indent}  {f} ({size:,}B)")

    result = "\n".join(lines) if lines else "(empty workspace)"
    if total_files > max_items:
        result += f"\n... ({total_files - max_items:,} more items)"
    return result
