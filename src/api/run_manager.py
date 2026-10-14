"""Agent Run Lifecycle and WebSocket event dispatcher."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from src.core.agent import CodingAgent
from src.core.events import AgentEvent, EventType
from src.core.settings import settings
from src.db.database import db
from src.llm.openai_provider import OpenAICompatibleProvider
from src.llm.protocol import LLMProvider
from src.workspace.base import Workspace
from src.workspace.manager import workspace_manager

logger = logging.getLogger("codecrafter.api.runs")

# Concurrency limits
MAX_CONCURRENT_RUNS = 10
PERSISTENCE_MAX_EVENTS = 200

# Track file changes per run for diff review
@dataclass
class RunChangeRecord:
    """Records file modifications made during an agent run."""
    run_id: str
    changes: dict[str, dict] = field(default_factory=dict)
    # Maps file_path -> {old_content, new_content, timestamp, operation}

    def record_change(self, file_path: str, old_content: str, new_content: str) -> None:
        """Record a file modification during agent execution."""
        import time
        self.changes[file_path] = {
            "old_content": old_content,
            "new_content": new_content,
            "timestamp": time.time(),
            "operation": "edit",
        }

    def get_changes(self) -> dict[str, dict]:
        """Get all recorded changes for this run."""
        return self.changes

    def has_changes(self) -> bool:
        """Check if any changes were recorded."""
        return bool(self.changes)

class RunManager:
    """Coordinates active agent runs, cancellation events, and event broadcast queues."""

    def __init__(self):
        self._cancellation_events: dict[str, asyncio.Event] = {}
        self._event_queues: dict[str, list[asyncio.Queue[AgentEvent]]] = {}
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._provider: LLMProvider | None = None
        # Concurrency control
        self._run_semaphore = asyncio.Semaphore(MAX_CONCURRENT_RUNS)
        self._active_runs: dict[str, dict[str, Any]] = {}
        # Event history for replay (persisted via database)
        self._event_buffer: dict[str, list[AgentEvent]] = {}

    def get_provider(self) -> LLMProvider:
        """Get or initialize default LLM provider."""
        if not self._provider:
            self._provider = OpenAICompatibleProvider(
                base_url=settings.LLM_BASE_URL,
                api_key=settings.LLM_API_KEY,
                model=settings.LLM_MODEL,
                timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
                max_retries=settings.LLM_MAX_RETRIES,
                default_temperature=settings.LLM_TEMPERATURE,
            )
        return self._provider

    def set_provider(self, provider: LLMProvider) -> None:
        """Override provider (e.g. for mock tests)."""
        self._provider = provider

    def subscribe(self, run_id: str) -> asyncio.Queue[AgentEvent]:
        """Subscribe to live events for a run."""
        queue: asyncio.Queue[AgentEvent] = asyncio.Queue()
        if run_id not in self._event_queues:
            self._event_queues[run_id] = []
        self._event_queues[run_id].append(queue)
        # Persist event history for replay
        if run_id not in self._event_buffer:
            self._event_buffer[run_id] = []
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[AgentEvent]) -> None:
        """Unsubscribe queue from run events."""
        if run_id in self._event_queues:
            if queue in self._event_queues[run_id]:
                self._event_queues[run_id].remove(queue)
            if not self._event_queues[run_id]:
                del self._event_queues[run_id]

    def record_run_changes(self, run_id: str) -> RunChangeRecord:
        """Get or create a ChangeRecord for tracking file modifications."""
        if run_id not in self._run_changes:
            self._run_changes[run_id] = RunChangeRecord(run_id=run_id)
        return self._run_changes[run_id]

    async def broadcast(self, run_id: str, event: AgentEvent) -> None:
        """Dispatch event to database and all active subscriber queues."""
        # Persist event to database
        await db.record_event(
            run_id=run_id,
            sequence=event.sequence,
            event_type=event.type.value,
            payload=event.data,
            timestamp=event.timestamp,
        )
        # Buffer event for replay (keep last N events per run)
        if run_id in self._event_buffer:
            self._event_buffer[run_id].append(event)
            if len(self._event_buffer[run_id]) > PERSISTENCE_MAX_EVENTS:
                self._event_buffer[run_id] = self._event_buffer[run_id][-PERSISTENCE_MAX_EVENTS:]
        # Broadcast to active WebSockets
        queues = self._event_queues.get(run_id, [])
        for q in queues:
            await q.put(event)

    async def cancel_run(self, run_id: str) -> bool:
        """Signal cancellation for an active run."""
        event = self._cancellation_events.get(run_id)
        if event:
            event.set()
            await db.update_run_status(run_id, "cancelled", error="Cancelled by user")
            return True
        return False

    async def start_run(
        self,
        project_id: str,
        session_id: str,
        prompt: str,
        run_id: str | None = None,
    ) -> str:
        """Initialize and launch an asynchronous agent run in the background."""
        r_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
        cancel_evt = asyncio.Event()
        self._cancellation_events[r_id] = cancel_evt

        # Acquire concurrency slot (will block if at limit)
        async with self._run_semaphore:
            # Persist run record
            await db.create_run(
                run_id=r_id,
                session_id=session_id,
                project_id=project_id,
                prompt=prompt,
            )

            # Add user message to session
            msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            await db.add_message(
                message_id=msg_id,
                session_id=session_id,
                role="user",
                content=prompt,
            )

            # Launch background execution task
            task = asyncio.create_task(
                self._execute_run(
                    run_id=r_id,
                    project_id=project_id,
                    session_id=session_id,
                    prompt=prompt,
                    cancel_evt=cancel_evt,
                )
            )
            self._active_tasks[r_id] = task
            self._active_runs[r_id] = {
                "started_at": asyncio.get_event_loop().time(),
                "status": "running",
                "project_id": project_id,
                "session_id": session_id,
            }
            return r_id

    async def _execute_run(
        self,
        run_id: str,
        project_id: str,
        session_id: str,
        prompt: str,
        cancel_evt: asyncio.Event,
    ) -> None:
        """Background worker executing the agent loop and recording state transitions."""

        await db.update_run_status(run_id, "running")
        project = await db.get_project(project_id)
        workspace_path = project["workspace_path"] if project else None

        workspace: Workspace = workspace_manager.get_workspace(
            workspace_id=project_id,
            custom_path=workspace_path,
        )

        # Retrieve prior session messages for context
        prior_messages_db = await db.get_messages(session_id)
        conversation_history: list[dict[str, Any]] = [
            {"role": m["role"], "content": m["content"]}
            for m in prior_messages_db[:-1]  # exclude the newly added user message
        ]

        agent = CodingAgent(provider=self.get_provider())
        final_text = ""
        run_status = "completed"
        error_msg = None

        try:
            async for event in agent.run(
                prompt=prompt,
                workspace=workspace,
                session_id=session_id,
                run_id=run_id,
                conversation_history=conversation_history,
                cancellation_event=cancel_evt,
            ):
                await self.broadcast(run_id, event)

                # Track file changes from agent operations
                if event.type == EventType.FILE_MODIFIED:
                    file_path = event.data.get("path", "")
                    # Get current file content before next operation
                    try:
                        current_content = await workspace.read_file(file_path)
                        change_record = self.record_run_changes(run_id)
                        change_record.record_change(
                            file_path,
                            event.data.get("old_content", current_content),
                            current_content,
                        )
                    except Exception:
                        pass

                if event.type == EventType.AGENT_MESSAGE:
                    final_text = event.data.get("content", "")
                elif event.type == EventType.AGENT_CANCELLED:
                    run_status = "cancelled"
                    error_msg = event.data.get("reason", "Cancelled")
                elif event.type == EventType.AGENT_FAILED:
                    run_status = "failed"
                    error_msg = event.data.get("error", "Agent failed")

        except Exception as exc:
            logger.exception("Unexpected exception in agent execution run %s: %s", run_id, exc)
            run_status = "failed"
            error_msg = str(exc)
            fail_event = AgentEvent(
                type=EventType.AGENT_FAILED,
                run_id=run_id,
                sequence=9999,
                data={"error": error_msg},
            )
            await self.broadcast(run_id, fail_event)

        finally:
            await db.update_run_status(run_id, run_status, error=error_msg)

            # Record assistant final message if present
            if final_text:
                asst_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
                await db.add_message(
                    message_id=asst_msg_id,
                    session_id=session_id,
                    role="assistant",
                    content=final_text,
                )

            # Cleanup cancellation event & task tracking
            self._cancellation_events.pop(run_id, None)
            self._active_tasks.pop(run_id, None)
            # Release concurrency slot
            self._active_runs.pop(run_id, None)


run_manager = RunManager()
