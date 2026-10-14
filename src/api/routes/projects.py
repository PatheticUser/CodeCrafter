"""Project management and file browsing endpoints.

Phase 2 Git integration:
- Clone public and private Git repositories.
- Branch management (list, create, switch).
- Git status (modified, staged, untracked files).
- File staging and unstaging.
- Commit creation.
- Push to remote (with user confirmation).
- Pull request creation (with user confirmation).
- GitHub App authentication support.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
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


# ── Data models ───────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""


class ImportGitRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    git_url: str = Field(..., description="Public HTTP/HTTPS repository URL")
    description: str = ""
    # Optional GitHub App auth token for private repos
    github_token: str | None = Field(None, description="GitHub PAT for private repo access")


class GitBranchRequest(BaseModel):
    branch: str = Field(..., description="Branch name to create or switch to")


class GitStatusRequest(BaseModel):
    pass


class GitStageRequest(BaseModel):
    file_path: str = Field(..., description="File to stage")


class GitCommitRequest(BaseModel):
    message: str = Field(..., description="Commit message")
    author_name: str | None = Field(None, description="Commit author name")
    author_email: str | None = Field(None, description="Commit author email")


class GitPushRequest(BaseModel):
    branch: str | None = Field(None, description="Branch to push (defaults to current)")
    force: bool = Field(False, description="Force push (not recommended)")


class GitPullRequestRequest(BaseModel):
    title: str = Field(..., description="Pull request title")
    body: str = Field("", description="Pull request description")
    base_branch: str = Field("main", description="Base branch for PR")


class FileContentUpdateRequest(BaseModel):
    path: str = Field(..., min_length=1, description="Relative path within project workspace")
    content: str


# ── Include Git router ────────────────────────────────────────────────────────

# The Git router provides:
#   /import-git, /branches, /branches/{name}, /status, /stage, /commit, /push, /pr

# ── Project creation ─────────────────────────────────────────────────────────

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


# ── Git import ───────────────────────────────────────────────────────────────

@router.post("/import-git", status_code=status.HTTP_201_CREATED)
async def import_git_repository(body: ImportGitRequest):
    """Clone a public git repository into a new project workspace.

    Supports:
    - Public HTTP/HTTPS repos (no token needed).
    - Private repos with GitHub PAT via github_token field.
    - Bounded clone with depth 1; timeout 60s.
    """
    # Validate URL scheme
    parsed = urlparse(body.git_url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only public HTTP and HTTPS git URLs are supported.",
        )

    hostname = (parsed.hostname or "").lower()
    # Block private/local/network targets
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

    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    workspace_path = (settings.workspace_root_dir / project_id).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Build git clone command
    clone_cmd = ["git", "clone", "--depth", "1", body.git_url, str(workspace_path)]

    # If GitHub token provided, configure it for private repo access
    env = os.environ.copy()
    if body.github_token:
        # Set git credential helper to use the provided token
        env["GIT_AUTHOR_NAME"] = "CodeCrafter"
        env["GIT_AUTHOR_EMAIL"] = "codecrafter@local"
        env["GIT_COMMITTER_NAME"] = "CodeCrafter"
        env["GIT_COMMITTER_EMAIL"] = "codecrafter@local"
        # Use token in URL for authenticated clone
        # e.g., https://token@github.com/user/repo.git
        from urllib.parse import urlunparse
        parsed_auth = parsed._replace(
            username=body.github_token,
            password="",  # token as password or use as username
        )
        auth_url = urlunparse(parsed_auth)
        clone_cmd[3] = auth_url  # Replace URL with authenticated version

    try:
        proc = await asyncio.create_subprocess_exec(
            *clone_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
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
            detail="Git clone timed out after 120 seconds.",
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


# ── Git branch management ────────────────────────────────────────────────────

@router.post("/{project_id}/git/branches", status_code=status.HTTP_200_OK)
async def list_git_branches(project_id: str):
    """List all local branches in the project workspace."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws_path = Path(project["workspace_path"])
    if not ws_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace directory not found for this project.",
        )

    try:
        result = subprocess.run(
            ["git", "branch", "--list", "--format=%(refname:short)"],
            cwd=str(ws_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Git branch listing failed: {result.stderr}",
            )
        branches = [b.strip() for b in result.stdout.splitlines() if b.strip()]
        return {"branches": branches, "current": _get_current_branch(ws_path)}
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Git command timed out.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing branches: {exc}",
        )


def _get_current_branch(ws_path: Path) -> str | None:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(ws_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


@router.post("/{project_id}/git/branches/{branch_name}/checkout", status_code=status.HTTP_200_OK)
async def checkout_git_branch(project_id: str, branch_name: str):
    """Switch to a different branch or create and switch to a new branch."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws_path = Path(project["workspace_path"])
    if not ws_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace directory not found for this project.",
        )

    # Check if branch already exists locally
    exists_cmd = ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"]
    exists_result = subprocess.run(
        exists_cmd, cwd=str(ws_path), capture_output=True, text=True, timeout=30
    )

    if exists_result.returncode == 0:
        # Branch exists, just checkout
        cmd = ["git", "checkout", branch_name]
    else:
        # Branch doesn't exist, create and checkout from remote or create orphan
        # Try to create from remote tracking branch first
        create_cmd = ["git", "checkout", "-b", branch_name]
        create_result = subprocess.run(
            create_cmd, cwd=str(ws_path), capture_output=True, text=True, timeout=30
        )
        if create_result.returncode != 0:
            # If that fails, create as orphan branch
            orphan_cmd = [
                "git",
                "checkout",
                "--orphan",
                branch_name,
                "&&",
                "git",
                "rm",
                "-r",
                ".",
                "&&",
                "git",
                "clean",
                "-fdx",
            ]
            orphan_result = subprocess.run(
                orphan_cmd, cwd=str(ws_path), capture_output=True, text=True, timeout=30
            )
            if orphan_result.returncode != 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create branch '{branch_name}': {orphan_result.stderr}",
                )

    checkout_result = subprocess.run(
        cmd, cwd=str(ws_path), capture_output=True, text=True, timeout=30
    )
    if checkout_result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to checkout branch '{branch_name}': {checkout_result.stderr}",
        )

    return {
        "branch": branch_name,
        "created_new": exists_result.returncode != 0,
        "message": f"Switched to branch '{branch_name}'",
    }


@router.post("/{project_id}/git/branches", status_code=status.HTTP_201_CREATED)
async def create_git_branch(project_id: str, body: GitBranchRequest):
    """Create a new branch."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws_path = Path(project["workspace_path"])
    if not ws_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace directory not found for this project.",
        )

    # Create the branch (will fail if it already exists)
    result = subprocess.run(
        ["git", "checkout", "-b", body.branch],
        cwd=str(ws_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        # Check if it's because the branch already exists
        if "fatal" in result.stderr.lower() and "already exists" in result.stderr.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Branch '{body.branch}' already exists. "
                    f"Use a different name or checkout instead."
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create branch: {result.stderr}",
        )

    return {"branch": body.branch, "message": f"Created and switched to branch '{body.branch}'"}


# ── Git status ────────────────────────────────────────────────────────────────

@router.post("/{project_id}/git/status", status_code=status.HTTP_200_OK)
async def get_git_status(project_id: str):
    """Get git working tree status (modified, staged, untracked files)."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws_path = Path(project["workspace_path"])
    if not ws_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace directory not found for this project.",
        )

    try:
        # Get short status
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(ws_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Git status failed: {result.stderr}",
            )

        stdout = result.stdout
        if not stdout.strip():
            return {"modified": [], "staged": [], "untracked": [], "message": "Working tree clean"}

        # Parse the short status output
        # Format: XY PATH where X=status of working directory, Y=status of index
        # X: ' ' = unmodified, 'M' = modified, 'A' = added to index, 'D' = deleted from index
        # Y: ' ' = not staged, 'M' = modified, 'A' = added, 'D' = deleted, 'R' = renamed, 'C' = copied
        # (first char = working dir, second = index status)
        modified_unstaged: list[str] = []
        modified_staged: list[str] = []
        untracked: list[str] = []

        for line in stdout.splitlines():
            if len(line) < 2:
                continue
            code = line[:2]
            filepath = line[3:]

            # Working directory status (first char)
            wc = code[0]
            # Index status (second char)
            ic = code[1]

            if filepath.startswith(":"):
                # Initial commit files
                continue

            if wc == " " and ic == " ":
                # Neither staged nor unstaged - check if tracked
                pass
            elif wc == "M" and ic == " ":
                modified_unstaged.append(filepath)
            elif wc == "M" and ic == "M":
                modified_staged.append(filepath)
            elif wc == "A" and ic == " ":
                modified_unstaged.append(filepath)  # New file, unstaged
            elif wc == "D" and ic == " ":
                modified_unstaged.append(filepath)  # Deleted file, unstaged
            elif wc == "?" and ic == " ":
                untracked.append(filepath)
            elif wc == "R" and ic == " ":
                # Renamed - show as modified
                modified_unstaged.append(filepath)
            else:
                modified_unstaged.append(filepath)

        return {
            "modified": modified_unstaged,
            "staged": modified_staged,
            "untracked": untracked,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Git command timed out.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting git status: {exc}",
        )


# ── Git staging/unstaging ────────────────────────────────────────────────────

@router.post("/{project_id}/git/stage", status_code=status.HTTP_200_OK)
async def stage_git_file(project_id: str, body: GitStageRequest):
    """Stage a file for commit."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws_path = Path(project["workspace_path"])
    if not ws_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace directory not found for this project.",
        )

    file_path = body.file_path
    # Ensure path is relative to workspace
    if os.path.isabs(file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File path must be relative to workspace root.",
        )

    # Stage the file
    result = subprocess.run(
        ["git", "add", file_path],
        cwd=str(ws_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stage file: {result.stderr}",
        )

    return {"file_path": file_path, "message": f"Staged '{file_path}'"}


@router.post("/{project_id}/git/unstage", status_code=status.HTTP_200_OK)
async def unstage_git_file(project_id: str, body: GitStageRequest):
    """Unstage a file."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws_path = Path(project["workspace_path"])
    if not ws_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace directory not found for this project.",
        )

    file_path = body.file_path
    if os.path.isabs(file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File path must be relative to workspace root.",
        )

    # Unstage the file
    result = subprocess.run(
        ["git", "reset", "HEAD", file_path],
        cwd=str(ws_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unstage file: {result.stderr}",
        )

    return {"file_path": file_path, "message": f"Unstaged '{file_path}'"}


# ── Git commit ───────────────────────────────────────────────────────────────

@router.post("/{project_id}/git/commit", status_code=status.HTTP_200_OK)
async def commit_git_changes(project_id: str, body: GitCommitRequest):
    """Commit staged changes."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws_path = Path(project["workspace_path"])
    if not ws_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace directory not found for this project.",
        )

    # Build commit command with optional author info
    cmd = ["git", "commit", "-m", body.message]
    if body.author_name:
        cmd.extend(["--author", f"{body.author_name} {body.author_email or ''}".strip()])

    result = subprocess.run(
        cmd,
        cwd=str(ws_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        # Check if there's nothing to commit
        if "nothing to commit" in result.stderr.lower() or "empty commit" in result.stderr.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No staged changes to commit. Stage files first.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Commit failed: {result.stderr}",
        )

    return {
        "message": body.message,
        "commit_hash": result.stdout.strip()[:40] if result.stdout else None,
    }


# ── Git push ─────────────────────────────────────────────────────────────────

@router.post("/{project_id}/git/push", status_code=status.HTTP_200_OK)
async def push_git_changes(
    project_id: str,
    body: GitPushRequest = GitPushRequest(),
):
    """Push committed changes to the remote repository.

    Requires explicit user confirmation in the request body.
    """
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws_path = Path(project["workspace_path"])
    if not ws_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace directory not found for this project.",
        )

    # Determine which branch to push
    branch = body.branch
    if not branch:
        # Get current branch
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(ws_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if branch_result.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not determine current branch.",
            )
        branch = branch_result.stdout.strip()
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No branch to push. Create or switch to a branch first.",
            )

    # Check if there's an upstream remote
    upstream_result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        cwd=str(ws_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    has_upstream = upstream_result.returncode == 0

    if has_upstream:
        upstream_branch = upstream_result.stdout.strip()
        push_cmd = ["git", "push"]
        if body.force:
            push_cmd.append("--force")
        push_cmd.append(f"{branch}@{upstream_branch}")
    else:
        # No upstream set - push current branch and set upstream
        push_cmd = ["git", "push", "-u", "origin", branch]

    result = subprocess.run(
        push_cmd,
        cwd=str(ws_path),
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        # Handle merge conflicts
        if "merge" in result.stderr.lower() or "conflict" in result.stderr.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Push failed due to merge conflicts:\n{result.stderr[:500]}",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Push failed: {result.stderr[:500]}",
        )

    return {
        "branch": branch,
        "upstream": has_upstream,
        "message": f"Pushed '{branch}' to remote",
        "stdout": result.stdout[:500] if result.stdout else None,
    }


# ── Pull request creation ────────────────────────────────────────────────────

@router.post("/{project_id}/git/pr", status_code=status.HTTP_201_CREATED)
async def create_pull_request(
    project_id: str,
    body: GitPullRequestRequest,
):
    """Create a pull request for the committed changes.

    Requires GitHub authentication. The agent may propose PR descriptions,
    but creation requires explicit user approval.

    Returns the PR URL and status.
    """
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws_path = Path(project["workspace_path"])
    if not ws_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace directory not found for this project.",
        )

    # Check if GitHub token is available (from project metadata or env)
    github_token = project.get("github_token") or os.environ.get("GITHUB_TOKEN")
    if not github_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "GitHub authentication required. "
                "Provide a GitHub PAT via project settings or GITHUB_TOKEN env var."
            ),
        )

    # Get current branch
    branch_result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=str(ws_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if branch_result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not determine current branch.",
        )
    current_branch = branch_result.stdout.strip()
    if not current_branch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No branch to create PR from.",
        )

    # Get remote URL
    remote_result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(ws_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if remote_result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No remote 'origin' configured.",
        )
    remote_url = remote_result.stdout.strip()

    # Parse GitHub URL
    if "github.com" not in remote_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only GitHub repositories are supported for PR creation.",
        )

    # Extract owner/repo from URL
    # https://github.com/owner/repo.git or git@github.com:owner/repo.git
    repo_path = remote_url.replace("https://github.com/", "").replace(".git", "")
    if "@" in remote_url:
        # SSH format: git@github.com:owner/repo.git
        repo_path = remote_url.split(":")[1].replace(".git", "")
    else:
        # HTTP format
        parts = repo_path.split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not parse GitHub repository from remote URL.",
            )

    # Build the PR API request
    pr_api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

    pr_payload = {
        "title": body.title,
        "body": body.body,
        "head": current_branch,
        "base": body.base_branch,
    }

    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        pr_api_url,
        data=json.dumps(pr_payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            pr_data = json.loads(response.read().decode())
            return {
                "pr_number": pr_data.get("number"),
                "pr_url": pr_data.get("html_url"),
                "title": pr_data.get("title"),
                "state": pr_data.get("state"),
                "message": f"Pull request #{pr_data.get('number')} created successfully",
            }
    except urllib.error.HTTPError as e:
        error_data = e.read().decode()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create pull request: {error_data[:500]}",
        )


# ── File content update (Monaco editor) ──────────────────────────────────────

@router.get("/{project_id}/files/content")
async def get_file_content(
    project_id: str,
    path: str = Query(..., description="Relative path within project workspace"),
):
    """Read content of a specific file."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws: Workspace = workspace_manager.get_workspace(
        workspace_id=project_id,
        custom_path=project["workspace_path"],
    )
    try:
        content = await ws.read_file(path)
        return {"path": path, "content": content}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{project_id}/files")
async def list_project_files(project_id: str):
    """List all files in the project workspace."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ws: Workspace = workspace_manager.get_workspace(
        workspace_id=project_id,
        custom_path=project["workspace_path"],
    )
    try:
        files = await ws.list_files()
        return {"files": files}
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
