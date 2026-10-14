"""Backwards compatibility shim for legacy core imports."""

from src.core.agent import CodingAgent
from src.core.settings import settings
from src.workspace.local import LocalWorkspace

__all__ = ["CodingAgent", "settings", "LocalWorkspace"]
