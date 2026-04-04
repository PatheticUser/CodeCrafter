"""Base command class and registry for built-in CLI commands.

Inspired by Claude Code's commands/ directory — slash commands like
/help, /sessions, /clear are handled by discrete Command classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseCommand(ABC):
    """Abstract base class for built-in CLI commands."""

    name: str = ""
    aliases: list[str] = []
    description: str = ""

    @abstractmethod
    def execute(self, args: str, context: dict[str, Any]) -> bool:
        """Execute the command.

        Args:
            args: Remaining text after the command name.
            context: Dict with shared state (session_mgr, user_name, etc.)

        Returns:
            True if the main loop should `continue` (skip LLM call).
        """
        ...

    def matches(self, input_lower: str) -> tuple[bool, str]:
        """Check if input matches this command. Returns (matched, remaining_args)."""
        for prefix in [self.name] + self.aliases:
            if input_lower == prefix:
                return True, ""
            if input_lower.startswith(prefix + " "):
                return True, input_lower[len(prefix) + 1:].strip()
        return False, ""


class CommandRegistry:
    """Registry of all built-in commands."""

    def __init__(self) -> None:
        self._commands: list[BaseCommand] = []

    def register(self, command: BaseCommand) -> None:
        self._commands.append(command)

    def try_handle(self, raw_input: str, context: dict[str, Any]) -> bool | None:
        """Try to match and execute a command.

        Returns:
            True  — command matched and handled, main loop should continue.
            None  — no command matched, proceed with LLM call.
        """
        input_lower = raw_input.strip().lower()
        for cmd in self._commands:
            matched, args = cmd.matches(input_lower)
            if matched:
                cmd.execute(args, context)
                return True
        return None

    @property
    def all_commands(self) -> list[BaseCommand]:
        return list(self._commands)
