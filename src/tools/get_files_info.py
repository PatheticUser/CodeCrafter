"""Tool: get_files_info — lists files and metadata in workspace."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.workspace.base import Workspace
from src.workspace.local import LocalWorkspace


async def get_files_info(
    workspace: Workspace | Path | str,
    directory: str = ".",
    verbose: bool = True,
) -> list[dict[str, Any]] | str:
    """Recursively list files in a directory within workspace with metadata."""
    if isinstance(workspace, (str, Path)):
        ws: Workspace = LocalWorkspace(workspace_id="local", root_dir=workspace)
    else:
        ws = workspace

    try:
        files = await ws.list_files(directory)
        if verbose and files:
            for f in files[:20]:
                print(f"Found: {f['path']} | Size: {f['size_kb']} KB | Modified: {f['modified']}")
            if len(files) > 20:
                print(f"... and {len(files) - 20} more files")
        return files
    except Exception as e:
        return f"Error listing directory '{directory}': {e}"


schema_get_files_info = {
    "type": "function",
    "function": {
        "name": "get_files_info",
        "description": "List files in a directory with sizes and dates. Stays inside workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": (
                        "Directory to list, relative to workspace. Default: workspace root."
                    ),
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Print detailed info per file.",
                },
            },
            "required": [],
        },
    },
}
