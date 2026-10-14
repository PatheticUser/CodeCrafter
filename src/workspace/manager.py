"""Workspace lifecycle manager for multi-project execution."""

from __future__ import annotations

from pathlib import Path

from src.core.settings import WorkspaceBackend, settings
from src.workspace.base import Workspace
from src.workspace.docker import DockerWorkspace
from src.workspace.local import LocalWorkspace


class WorkspaceManager:
    """Manages active workspace instances across projects."""

    def __init__(self, root_dir: Path | str | None = None):
        self.root_dir = Path(root_dir or settings.workspace_root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._workspaces: dict[str, Workspace] = {}

    def get_workspace(
        self,
        workspace_id: str,
        backend: WorkspaceBackend | str | None = None,
        custom_path: Path | str | None = None,
    ) -> Workspace:
        """Retrieve existing or construct a new isolated workspace."""
        if workspace_id in self._workspaces:
            return self._workspaces[workspace_id]

        selected_backend = backend or settings.WORKSPACE_BACKEND
        if isinstance(selected_backend, str):
            selected_backend = WorkspaceBackend(selected_backend.lower())

        ws_dir = (
            Path(custom_path).resolve() if custom_path else (self.root_dir / workspace_id).resolve()
        )
        ws_dir.mkdir(parents=True, exist_ok=True)

        if selected_backend == WorkspaceBackend.DOCKER:
            ws = DockerWorkspace(
                workspace_id=workspace_id,
                root_dir=ws_dir,
                image=settings.WORKSPACE_CONTAINER_IMAGE,
                command_timeout=settings.WORKSPACE_COMMAND_TIMEOUT,
                max_output_bytes=settings.WORKSPACE_MAX_OUTPUT_BYTES,
            )
        else:
            ws = LocalWorkspace(
                workspace_id=workspace_id,
                root_dir=ws_dir,
                command_timeout=settings.WORKSPACE_COMMAND_TIMEOUT,
                max_output_bytes=settings.WORKSPACE_MAX_OUTPUT_BYTES,
            )

        self._workspaces[workspace_id] = ws
        return ws

    async def cleanup_all(self) -> None:
        """Cleanup all active containerized workspaces."""
        for ws in self._workspaces.values():
            if isinstance(ws, DockerWorkspace):
                await ws.cleanup()
        self._workspaces.clear()


workspace_manager = WorkspaceManager()
