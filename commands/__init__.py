"""Commands package — auto-registers all built-in commands."""

from commands.base import CommandRegistry
from commands.help import HelpCommand
from commands.sessions import (
    SessionsListCommand,
    SessionNewCommand,
    SessionLoadCommand,
    SessionDeleteCommand,
    ClearCommand,
    ExitCommand,
)


def create_command_registry() -> CommandRegistry:
    """Create and populate the command registry."""
    registry = CommandRegistry()
    registry.register(HelpCommand())
    registry.register(ExitCommand())
    registry.register(SessionsListCommand())
    registry.register(SessionNewCommand())
    registry.register(SessionLoadCommand())
    registry.register(SessionDeleteCommand())
    registry.register(ClearCommand())
    return registry


__all__ = ["create_command_registry", "CommandRegistry"]
