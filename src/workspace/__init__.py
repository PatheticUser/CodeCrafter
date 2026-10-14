"""Workspace abstraction module."""

from src.workspace.base import CommandResult, Workspace
from src.workspace.docker import DockerWorkspace
from src.workspace.local import LocalWorkspace
from src.workspace.manager import WorkspaceManager, workspace_manager
from src.workspace.security import SecurityError, is_command_blocked, resolve_safe_path

__all__ = [
    "Workspace",
    "CommandResult",
    "LocalWorkspace",
    "DockerWorkspace",
    "WorkspaceManager",
    "workspace_manager",
    "SecurityError",
    "is_command_blocked",
    "resolve_safe_path",
]
