"""Tool registry — discovers canonical tools and dispatches execution against Workspace."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.workspace.base import Workspace
from src.workspace.local import LocalWorkspace


class ToolRegistry:
    """Registry providing tool schemas and executing tools against a Workspace."""

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._schemas: list[dict[str, Any]] = []
        self._discover()

    def _discover(self):
        """Register all 9 canonical tools."""
        from src.tools.delete_file import delete_file, schema_delete_file
        from src.tools.edit_file import edit_file, schema_edit_file
        from src.tools.get_file_content import get_file_content, schema_get_file_content
        from src.tools.get_file_outline import get_file_outline, schema_get_file_outline
        from src.tools.get_files_info import get_files_info, schema_get_files_info
        from src.tools.run_code import run_code, schema_run_code
        from src.tools.run_command import run_command, schema_run_command
        from src.tools.search_files import schema_search_files, search_files
        from src.tools.write_file import schema_write_file, write_file

        tool_defs = [
            ("get_files_info", get_files_info, schema_get_files_info),
            ("get_file_content", get_file_content, schema_get_file_content),
            ("get_file_outline", get_file_outline, schema_get_file_outline),
            ("write_file", write_file, schema_write_file),
            ("edit_file", edit_file, schema_edit_file),
            ("delete_file", delete_file, schema_delete_file),
            ("run_code", run_code, schema_run_code),
            ("run_command", run_command, schema_run_command),
            ("search_files", search_files, schema_search_files),
        ]

        for name, func, schema in tool_defs:
            self._tools[name] = func
            self._schemas.append(schema)

    async def execute(
        self, func_name: str, workspace_or_dir: Workspace | Path | str, **kwargs
    ) -> Any:
        """Execute a tool asynchronously against a Workspace."""
        if func_name not in self._tools:
            return f"Error: Unknown function '{func_name}'"

        if isinstance(workspace_or_dir, (str, Path)):
            workspace: Workspace = LocalWorkspace(workspace_id="local", root_dir=workspace_or_dir)
        else:
            workspace = workspace_or_dir

        try:
            func = self._tools[func_name]
            # Handle both async and sync tools
            import inspect

            if inspect.iscoroutinefunction(func):
                return await func(workspace, **kwargs)
            else:
                return func(workspace, **kwargs)
        except Exception as e:
            return f"ERROR executing {func_name}: {e}"

    def get_all_schemas(self) -> list[dict[str, Any]]:
        """Return all tool schemas for LLM function calling."""
        return list(self._schemas)

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._tools
