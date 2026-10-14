"""Project management and file browsing endpoints."""

from __future__ import annotations

import asyncio
import shutil
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.core.settings import settings
from src.db.database import db
from src.workspace.base import Workspace
from src.workspace.manager import workspace_manager

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""


class ImportGitRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    git_url: str = Field(..., description="Public HTTP/HTTPS repository URL")
    description: str = ""


class FileContentUpdateRequest(BaseModel):
    path: str = Field(..., min_length=1)
    content: str


def _validate_git_url(url: str) -> None:
    """Ensure git URL uses safe public HTTP/HTTPS protocol."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only public HTTP and HTTPS git URLs are supported.",
        )
    hostname = (parsed.hostname or "").lower()
    if (
        not hostname
        or hostname in ("localhost", "127.0.0.1", "::1")
        or hostname.startswith("10.")
        or hostname.startswith("192.168.")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Private, local, or loopback network targets are prohibited.",
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(body: CreateProjectRequest):
    """Create a new empty project."""
    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    workspace_path = (settings.workspace_root_dir / project_id).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)

    project = await db.create_project(
        project_id=project_id,
        name=body.name,
        workspace_path=str(workspace_path),
        description=body.description,
    )
    # Automatically seed an initial default session
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    await db.create_session(
        session_id=session_id,
        project_id=project_id,
        title="Initial Session",
    )
    project["default_session_id"] = session_id
    return project


@router.get("")
async def list_projects():
    """List all projects."""
    return await db.list_projects()


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete project and remove associated workspace directory."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Remove workspace directory if it exists
    ws_path = Path(project["workspace_path"])
    if ws_path.exists():
        try:
            shutil.rmtree(ws_path)
        except Exception:
            pass

    deleted = await db.delete_project(project_id)
    return {"deleted": deleted, "project_id": project_id}


@router.post("/import-git", status_code=status.HTTP_201_CREATED)
async def import_git_repository(body: ImportGitRequest):
    """Clone a public git repository into a new project workspace."""
    _validate_git_url(body.git_url)

    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    workspace_path = (settings.workspace_root_dir / project_id).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Perform bounded git clone with depth 1
    clone_cmd = [
        "git",
        "clone",
        "--depth",
        "1",
        body.git_url,
        str(workspace_path),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *clone_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            shutil.rmtree(workspace_path, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Git clone failed: {stderr.decode(errors='replace')}",
            )
    except TimeoutError:
        shutil.rmtree(workspace_path, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Git clone timed out after 60 seconds.",
        )
    except Exception as exc:
        shutil.rmtree(workspace_path, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cloning repository: {exc}",
        )

    project = await db.create_project(
        project_id=project_id,
        name=body.name,
        workspace_path=str(workspace_path),
        description=body.description,
        git_url=body.git_url,
    )

    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    await db.create_session(
        session_id=session_id,
        project_id=project_id,
        title="Git Import Session",
    )
    project["default_session_id"] = session_id
    return project


@router.get("/{project_id}/files")
async def get_project_files(project_id: str):
    """List all workspace files and visual directory tree."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws: Workspace = workspace_manager.get_workspace(
        workspace_id=project_id,
        custom_path=project["workspace_path"],
    )
    files = await ws.list_files()
    tree = await ws.scan_tree()
    return {"files": files, "tree": tree}


@router.get("/{project_id}/files/content")
async def get_file_content(
    project_id: str,
    path: str = Query(..., description="Relative path within project workspace"),
    start_line: int | None = Query(None),
    end_line: int | None = Query(None),
):
    """Read contents of a specific file."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws: Workspace = workspace_manager.get_workspace(
        workspace_id=project_id,
        custom_path=project["workspace_path"],
    )
    try:
        content = await ws.read_file(path, start_line=start_line, end_line=end_line)
        return {"path": path, "content": content}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.put("/{project_id}/files/content")
async def update_file_content(project_id: str, body: FileContentUpdateRequest):
    """Write/save content to a file in Monaco editor."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws: Workspace = workspace_manager.get_workspace(
        workspace_id=project_id,
        custom_path=project["workspace_path"],
    )
    try:
        result = await ws.write_file(body.path, body.content)
        return {"success": True, "message": result, "path": body.path}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
