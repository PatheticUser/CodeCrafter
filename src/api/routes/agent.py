"""Agent run lifecycle and WebSocket streaming routes."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from src.api.run_manager import run_manager
from src.core.events import EventType
from src.db.database import db

logger = logging.getLogger("codecrafter.api.agent")
router = APIRouter(prefix="/api/agent", tags=["agent"])


class StartRunRequest(BaseModel):
    project_id: str
    session_id: str
    prompt: str = Field(..., min_length=1)


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_agent_run(body: StartRunRequest):
    """Start an asynchronous coding agent run."""
    project = await db.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    session = await db.get_session(body.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    run_id = await run_manager.start_run(
        project_id=body.project_id,
        session_id=body.session_id,
        prompt=body.prompt,
    )
    return {"run_id": run_id, "status": "pending"}


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str):
    """Inspect run metadata and status."""
    run = await db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    """Cancel an active agent run."""
    run = await db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    cancelled = await run_manager.cancel_run(run_id)
    return {"cancelled": cancelled, "run_id": run_id}


@router.websocket("/runs/{run_id}/events")
async def websocket_run_events(
    websocket: WebSocket,
    run_id: str,
    since: int = Query(0, description="Resume sequence number for replay"),
):
    """Stream agent execution events over WebSocket with reconnection and replay."""
    await websocket.accept()

    # 1. Replay historical events
    past_events = await db.get_run_events(run_id, since_sequence=since)
    last_seq = since
    for ev in past_events:
        await websocket.send_text(json.dumps(ev))
        last_seq = max(last_seq, ev["sequence"])

    # 2. Check if run is already finished
    run = await db.get_run(run_id)
    if run and run["status"] in ("completed", "failed", "cancelled"):
        # Run already finished and all events sent
        await websocket.close()
        return

    # 3. Subscribe to live stream
    queue = run_manager.subscribe(run_id)

    try:
        while True:
            # Wait for next live event or client disconnect
            event = await queue.get()
            if event.sequence > last_seq:
                payload = {
                    "type": event.type.value,
                    "run_id": event.run_id,
                    "sequence": event.sequence,
                    "timestamp": event.timestamp,
                    "data": event.data,
                }
                await websocket.send_text(json.dumps(payload))
                last_seq = event.sequence

            # If terminal event emitted, finish stream
            if event.type in (
                EventType.AGENT_COMPLETED,
                EventType.AGENT_FAILED,
                EventType.AGENT_CANCELLED,
            ):
                break

    except WebSocketDisconnect:
        logger.info("Client disconnected from run WebSocket %s", run_id)
    except Exception as exc:
        logger.warning("Error in WebSocket streaming for run %s: %s", run_id, exc)
    finally:
        run_manager.unsubscribe(run_id, queue)
        try:
            await websocket.close()
        except Exception:
            pass
