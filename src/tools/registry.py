"""Tool registry — auto-discovers and provides a clean interface for tools."""

from __future__ import annotations

from typing import Any, Callable


class ToolRegistry:
    """Registry that auto-discovers tool functions and provides a clean interface.

    Usage:
        registry = ToolRegistry()
        result = registry.execute("write_file", working_dir, file_path="foo.txt", content="hello")
        schemas = registry.get_all_schemas()
    """

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._schemas: list[dict[str, Any]] = []
        self._discover()

    def _discover(self):
        """Discover all available tools and their schemas."""
        # Lazy imports to avoid circular dependencies
        from src.tools.delete_file import delete_file, schema_delete_file
        from src.tools.edit_file import edit_file, schema_edit_file
        from src.tools.get_file_content import get_file_content, schema_get_file_content
        from src.tools.get_file_outline import get_file_outline, schema_get_file_outline
        from src.tools.get_files_info import get_files_info, schema_get_files_info
        from src.tools.run_code import run_code, schema_run_code
        from src.tools.run_command import run_command, schema_run_command
        from src.tools.search_files import search_files, schema_search_files
        from src.tools.write_file import write_file, schema_write_file

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

    def execute(self, func_name: str, working_dir: str, **kwargs) -> str:
        """Execute a tool by name with given arguments.

        Args:
            func_name: The name of the tool to execute.
            working_dir: The sandboxed working directory.
            **kwargs: Arguments to pass to the tool function.

        Returns:
            The result string from the tool.
        """
        if func_name not in self._tools:
            return f"Error: Unknown function {func_name}"

        try:
            return self._tools[func_name](working_dir, **kwargs)
        except Exception as e:
            return f"ERROR executing {func_name}: {e}"

    def get_all_schemas(self) -> list[dict[str, Any]]:
        """Return all tool schemas for LLM function calling."""
        return list(self._schemas)

    def get_tool_names(self) -> list[str]:
        """Return all registered tool names."""
        return list(self._tools.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._tools
