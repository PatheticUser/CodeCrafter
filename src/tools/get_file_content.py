"""Tool: get_file_content — read file contents with line range support."""

from __future__ import annotations

from pathlib import Path

from src.workspace.base import Workspace
from src.workspace.local import LocalWorkspace


async def get_file_content(
    workspace: Workspace | Path | str,
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Read a file within the workspace safely."""
    if isinstance(workspace, (str, Path)):
        ws: Workspace = LocalWorkspace(workspace_id="local", root_dir=workspace)
    else:
        ws = workspace

    try:
        return await ws.read_file(file_path, start_line=start_line, end_line=end_line)
    except Exception as e:
        return f"Error: {e}"


schema_get_file_content = {
    "type": "function",
    "function": {
        "name": "get_file_content",
        "description": (
            "Read a file. Small files (<300 lines) return fully. "
            "Large files show head+tail with line ranges."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "File path relative to workspace.",
                },
                "start_line": {
                    "type": "integer",
                    "description": "1-based start line (optional).",
                },
                "end_line": {
                    "type": "integer",
                    "description": "1-based end line inclusive (optional).",
                },
            },
            "required": ["file_path"],
        },
    },
}
