"""Conversation session management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.db.database import db

router = APIRouter(tags=["sessions"])


class CreateSessionRequest(BaseModel):
    project_id: str
    title: str = Field("New Session", max_length=100)


@router.post("/api/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(body: CreateSessionRequest):
    """Create a new session within a project."""
    project = await db.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    return await db.create_session(
        session_id=session_id,
        project_id=body.project_id,
        title=body.title,
    )


@router.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details and full conversation history."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages = await db.get_messages(session_id)
    return {
        "session": session,
        "messages": messages,
    }


@router.get("/api/projects/{project_id}/sessions")
async def list_project_sessions(project_id: str):
    """List all sessions for a specific project."""
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return await db.list_sessions(project_id)
