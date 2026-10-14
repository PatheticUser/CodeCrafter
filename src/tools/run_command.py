"""Tool: run_command — execute shell command inside workspace."""

from __future__ import annotations

from pathlib import Path

from src.workspace.base import CommandResult, Workspace
from src.workspace.local import LocalWorkspace


async def run_command(
    workspace: Workspace | Path | str,
    command: str,
    timeout: int = 30,
) -> str:
    """Executes a shell command inside the workspace."""
    if isinstance(workspace, (str, Path)):
        ws: Workspace = LocalWorkspace(workspace_id="local", root_dir=workspace)
    else:
        ws = workspace

    try:
        result: CommandResult = await ws.execute_command(command, timeout=timeout)
        return result.to_formatted_output()
    except Exception as e:
        return f"Error executing command: {e}"


schema_run_command = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": (
            "Run a shell command in the workspace. Use for: uv add, npm, git, build tools."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "Shell command to execute (e.g. 'uv add fastapi' or 'npm test')."
                    ),
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max seconds. Default 30.",
                },
            },
            "required": ["command"],
        },
    },
}
