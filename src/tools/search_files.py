"""Tool: search_files — grep-like pattern search in workspace."""

from __future__ import annotations

from pathlib import Path

from src.workspace.base import Workspace
from src.workspace.local import LocalWorkspace


async def search_files(
    workspace: Workspace | Path | str,
    pattern: str,
    directory: str = ".",
    file_extension: str | None = None,
    case_sensitive: bool = False,
) -> str:
    """Search through workspace files for a text or regex pattern."""
    if isinstance(workspace, (str, Path)):
        ws: Workspace = LocalWorkspace(workspace_id="local", root_dir=workspace)
    else:
        ws = workspace

    try:
        return await ws.search_files(
            pattern=pattern,
            directory=directory,
            file_extension=file_extension,
            case_sensitive=case_sensitive,
        )
    except Exception as e:
        return f"Error searching files for '{pattern}': {e}"


schema_search_files = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": (
            "Search files for a pattern (grep). Returns file:line matches, capped at 50. "
            "Supports regex and extension filter."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Text or regex pattern to search for.",
                },
                "directory": {
                    "type": "string",
                    "description": "Subdirectory to scope search. Default: workspace root.",
                },
                "file_extension": {
                    "type": "string",
                    "description": "Filter by extension, e.g. '.py'.",
                },
            },
            "required": ["pattern"],
        },
    },
}
