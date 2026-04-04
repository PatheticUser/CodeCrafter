"""Base tool class for CodeCrafter.

Inspired by Claude Code's Tool.ts pattern — every tool inherits from
`BaseTool`, which enforces a consistent interface and enables automatic
registration via the ToolRegistry.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for all CodeCrafter tools.

    Subclasses must define:
        name       — unique tool identifier (e.g. "write_file")
        description — human-readable description for the LLM
        parameters — JSON Schema dict for the tool's parameters
        execute()  — the actual implementation

    The base class provides common helpers like path validation.
    """

    # --- Subclass must override ---
    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}
    required: list[str] = []

    # Whether this tool mutates workspace files
    mutates_workspace: bool = False

    # Whether errors from this tool should trigger auto-fix
    auto_fixable: bool = False

    def __init__(self, working_directory: str) -> None:
        self.working_directory = os.path.abspath(working_directory)

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """Run the tool. Returns a result string (success or error)."""
        ...

    # --- Helpers ---

    def validate_path(self, relative_path: str) -> tuple[str, str | None]:
        """Resolve *relative_path* under the working directory.

        Returns:
            (absolute_path, None) on success.
            ("", error_message) if the path escapes the sandbox.
        """
        target = os.path.abspath(
            os.path.join(self.working_directory, relative_path)
        )
        if not (
            target == self.working_directory
            or target.startswith(self.working_directory + os.sep)
        ):
            return "", (
                f'Error: Cannot access "{relative_path}" — '
                f"outside the permitted working directory"
            )
        return target, None

    def file_must_exist(self, relative_path: str) -> tuple[str, str | None]:
        """Like validate_path but also checks the file exists."""
        abs_path, err = self.validate_path(relative_path)
        if err:
            return "", err
        if not os.path.isfile(abs_path):
            return "", f'Error: File not found: "{relative_path}"'
        return abs_path, None

    def dir_must_exist(self, relative_path: str) -> tuple[str, str | None]:
        """Like validate_path but also checks the directory exists."""
        abs_path, err = self.validate_path(relative_path)
        if err:
            return "", err
        if not os.path.isdir(abs_path):
            return "", f'Error: Directory not found: "{relative_path}"'
        return abs_path, None

    # --- Schema generation ---

    def to_schema(self) -> dict[str, Any]:
        """Generate the OpenAI-compatible tool schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                },
            },
        }

    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"
