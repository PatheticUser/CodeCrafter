"""Core modules for CodeCrafter."""

from .api_manager import OllamaClient
from .workspace import scan_workspace_tree

__all__ = ["OllamaClient", "scan_workspace_tree"]
