"""Tool: get_file_outline — outline classes, functions, and imports in a file."""

from __future__ import annotations

from pathlib import Path

from src.workspace.base import Workspace
from src.workspace.local import LocalWorkspace


async def get_file_outline(
    workspace: Workspace | Path | str,
    file_path: str,
) -> str:
    """Return skeleton of a file: imports, class definitions, function signatures."""
    if isinstance(workspace, (str, Path)):
        ws: Workspace = LocalWorkspace(workspace_id="local", root_dir=workspace)
    else:
        ws = workspace

    try:
        return await ws.get_file_outline(file_path)
    except Exception as e:
        return f"Error reading outline for '{file_path}': {e}"


schema_get_file_outline = {
    "type": "function",
    "function": {
        "name": "get_file_outline",
        "description": (
            "Show file structure: imports, classes, functions with line numbers. "
            "Use before reading large files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "File path relative to workspace.",
                },
            },
            "required": ["file_path"],
        },
    },
}
