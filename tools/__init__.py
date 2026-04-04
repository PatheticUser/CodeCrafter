"""Tool registry with auto-discovery.

Inspired by Claude Code's tools/ pattern — each tool is a class that
inherits from BaseTool, and the registry discovers them automatically.

Usage:
    from tools import ToolRegistry

    registry = ToolRegistry(working_directory="/path/to/workspace")
    schemas = registry.get_schemas()    # for the LLM
    result  = registry.execute("write_file", file_path="hello.py", content="...")
"""

from __future__ import annotations

import importlib
import os
import pkgutil
from typing import Any

from services.logger import logger
from tools.base import BaseTool


class ToolRegistry:
    """Auto-discovers and manages all registered tools."""

    def __init__(self, working_directory: str) -> None:
        self.working_directory = working_directory
        self._tools: dict[str, BaseTool] = {}
        self._discover()

    def _discover(self) -> None:
        """Walk the tools/ package and register every BaseTool subclass."""
        package_dir = os.path.dirname(__file__)
        for _importer, module_name, _is_pkg in pkgutil.iter_modules([package_dir]):
            if module_name in ("__init__", "base"):
                continue
            try:
                module = importlib.import_module(f"tools.{module_name}")
            except Exception as e:
                logger.warning("Failed to import tool module '%s': %s", module_name, e)
                continue

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseTool)
                    and attr is not BaseTool
                    and attr.name  # skip abstract / unnamed
                ):
                    instance = attr(self.working_directory)
                    self._tools[instance.name] = instance
                    logger.debug("Registered tool: %s", instance.name)

        logger.debug("Tool registry: %d tools loaded", len(self._tools))

    # --- Public API ---

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible tool schemas for all registered tools."""
        return [tool.to_schema() for tool in self._tools.values()]

    def execute(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a tool by name. Returns the tool's result."""
        tool = self._tools.get(tool_name)
        if tool is None:
            return f"Error: Unknown tool '{tool_name}'"
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            logger.error("Tool '%s' raised: %s", tool_name, e, exc_info=True)
            return f"ERROR executing {tool_name}: {e}"

    def get_tool(self, tool_name: str) -> BaseTool | None:
        """Get a tool instance by name."""
        return self._tools.get(tool_name)

    def is_mutating(self, tool_name: str) -> bool:
        """Check if a tool mutates workspace files."""
        tool = self._tools.get(tool_name)
        return tool.mutates_workspace if tool else False

    def is_auto_fixable(self, tool_name: str) -> bool:
        """Check if errors from this tool should trigger auto-fix."""
        tool = self._tools.get(tool_name)
        return tool.auto_fixable if tool else False

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<ToolRegistry: {', '.join(self.tool_names)}>"
