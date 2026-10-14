"""Workspace abstraction protocols and models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class CommandResult:
    """Normalized result of executing a command in a workspace."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    def to_formatted_output(self) -> str:
        """Format as human- and model-readable execution log."""
        if self.timed_out:
            return f"Error: Command timed out. STDERR:\n{self.stderr}"
        output_parts: list[str] = []
        if self.stdout.strip():
            output_parts.append(f"STDOUT:\n{self.stdout.strip()}")
        if self.stderr.strip():
            output_parts.append(f"STDERR:\n{self.stderr.strip()}")
        output_parts.append(f"EXIT CODE: {self.exit_code}")
        return (
            "\n".join(output_parts)
            if output_parts
            else f"Command completed (exit code {self.exit_code})"
        )


@runtime_checkable
class Workspace(Protocol):
    """Abstract interface for all workspace backends (local, containerized, remote)."""

    @property
    def workspace_id(self) -> str:
        """Unique identifier for this workspace instance."""
        ...

    async def list_files(self, directory: str = ".") -> list[dict[str, Any]]:
        """List files and metadata in a directory."""
        ...

    async def read_file(
        self,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        """Read full content or a line range of a file."""
        ...

    async def write_file(self, file_path: str, content: str) -> str:
        """Create or overwrite a file."""
        ...

    async def edit_file(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
    ) -> dict[str, Any] | str:
        """Targeted search and replace in a file."""
        ...

    async def delete_file(self, file_path: str) -> str:
        """Delete a file in the workspace."""
        ...

    async def search_files(
        self,
        pattern: str,
        directory: str = ".",
        file_extension: str | None = None,
        case_sensitive: bool = False,
    ) -> str:
        """Search text/regex in workspace files."""
        ...

    async def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
        """Run a shell command inside the workspace."""
        ...

    async def get_file_outline(self, file_path: str) -> str:
        """Return structural skeleton (classes, functions, imports) of a file."""
        ...

    async def scan_tree(self) -> str:
        """Return compact visual directory tree representation for context."""
        ...
