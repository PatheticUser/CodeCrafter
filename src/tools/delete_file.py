"""Tool: delete_file — delete a file within the workspace boundary."""

from __future__ import annotations

from pathlib import Path

from src.workspace.base import Workspace
from src.workspace.local import LocalWorkspace


async def delete_file(
    workspace: Workspace | Path | str,
    file_path: str,
) -> str:
    """Safely deletes a file within the workspace."""
    if isinstance(workspace, (str, Path)):
        ws: Workspace = LocalWorkspace(workspace_id="local", root_dir=workspace)
    else:
        ws = workspace

    try:
        return await ws.delete_file(file_path)
    except Exception as e:
        return f"Error deleting '{file_path}': {e}"


schema_delete_file = {
    "type": "function",
    "function": {
        "name": "delete_file",
        "description": "Delete a file. Only operates within workspace.",
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
