"""Tool: write_file — create or overwrite a file in workspace."""

from __future__ import annotations

from pathlib import Path

from src.workspace.base import Workspace
from src.workspace.local import LocalWorkspace


async def write_file(
    workspace: Workspace | Path | str,
    file_path: str,
    content: str,
) -> str:
    """Safely writes to a file within workspace, creating parent directories if needed."""
    if isinstance(workspace, (str, Path)):
        ws: Workspace = LocalWorkspace(workspace_id="local", root_dir=workspace)
    else:
        ws = workspace

    try:
        return await ws.write_file(file_path, content)
    except Exception as e:
        return f"Error: Failed to write to '{file_path}': {e}"


schema_write_file = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Create or overwrite a file. Creates parent directories if needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "File path relative to workspace.",
                },
                "content": {
                    "type": "string",
                    "description": "Full file content to write.",
                },
            },
            "required": ["file_path", "content"],
        },
    },
}
