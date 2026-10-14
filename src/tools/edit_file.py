"""Tool: edit_file — search and replace within a file with diff tracking."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.workspace.base import Workspace
from src.workspace.local import LocalWorkspace


async def edit_file(
    workspace: Workspace | Path | str,
    file_path: str,
    old_content: str,
    new_content: str,
) -> dict[str, Any] | str:
    """Targeted surgical edit: finds old_content and replaces with new_content."""
    if isinstance(workspace, (str, Path)):
        ws: Workspace = LocalWorkspace(workspace_id="local", root_dir=workspace)
    else:
        ws = workspace

    try:
        return await ws.edit_file(file_path, old_content, new_content)
    except Exception as e:
        return f"Error editing '{file_path}': {e}"


schema_edit_file = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": (
            "Search+replace within a file. Use for targeted edits. Shows file preview on mismatch."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "File path relative to workspace.",
                },
                "old_content": {
                    "type": "string",
                    "description": "Exact text to find (whitespace-sensitive).",
                },
                "new_content": {
                    "type": "string",
                    "description": "Replacement text.",
                },
            },
            "required": ["file_path", "old_content", "new_content"],
        },
    },
}
