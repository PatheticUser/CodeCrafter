"""Core modules: settings, API client, workspace scanner, agent loop."""

from src.core.agent import AgentLoop
from src.core.api_manager import OllamaClient
from src.core.settings import settings
from src.core.workspace import scan_workspace_tree

__all__ = [
    "settings",
    "OllamaClient",
    "scan_workspace_tree",
    "AgentLoop",
]
