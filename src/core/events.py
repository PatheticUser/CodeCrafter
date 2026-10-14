"""Structured event schemas emitted by the Agent during execution."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    """Supported agent and execution lifecycle event types."""

    AGENT_STARTED = "agent.started"
    AGENT_THINKING = "agent.thinking"
    AGENT_MESSAGE = "agent.message"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    FILE_CREATED = "file.created"
    FILE_MODIFIED = "file.modified"
    FILE_DELETED = "file.deleted"
    EXECUTION_OUTPUT = "execution.output"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_CANCELLED = "agent.cancelled"


class AgentEvent(BaseModel):
    """Structured event emitted across WebSocket and persisted in DB."""

    type: EventType
    run_id: str
    sequence: int
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    data: dict[str, Any] = Field(default_factory=dict)
