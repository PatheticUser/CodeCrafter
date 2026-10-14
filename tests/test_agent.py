"""Automated unit and integration tests for CodingAgent and LLM provider."""

import asyncio
from pathlib import Path

import pytest

from src.core.agent import CodingAgent
from src.core.events import EventType
from src.llm.mock_provider import MockLLMProvider
from src.llm.protocol import LLMResponse
from src.workspace.local import LocalWorkspace


@pytest.fixture
def test_env(tmp_path: Path):
    ws = LocalWorkspace(workspace_id="test-agent-ws", root_dir=tmp_path / "ws")
    mock_llm = MockLLMProvider()
    agent = CodingAgent(provider=mock_llm)
    return ws, mock_llm, agent


@pytest.mark.asyncio
async def test_agent_single_turn_text(test_env):
    ws, mock_llm, agent = test_env
    mock_llm.queue_text("Task completed successfully!")

    events = []
    async for event in agent.run(
        prompt="Explain recursion",
        workspace=ws,
        session_id="s1",
        run_id="r1",
    ):
        events.append(event)

    types = [e.type for e in events]
    assert EventType.AGENT_STARTED in types
    assert EventType.AGENT_THINKING in types
    assert EventType.AGENT_MESSAGE in types
    assert EventType.AGENT_COMPLETED in types

    # Check sequence monotonicity
    seqs = [e.sequence for e in events]
    assert seqs == list(range(1, len(events) + 1))


@pytest.mark.asyncio
async def test_agent_multi_step_tool_call(test_env):
    ws, mock_llm, agent = test_env

    # 1. First response calls write_file
    mock_llm.queue_tool_call(
        name="write_file",
        arguments={"file_path": "main.py", "content": "print('hello from tool')"},
        call_id="call_write_1",
    )
    # 2. Second response calls run_code to verify
    mock_llm.queue_tool_call(
        name="run_code",
        arguments={"path": "main.py"},
        call_id="call_run_2",
    )
    # 3. Third response gives final text
    mock_llm.queue_text("Created main.py and verified execution.")

    events = []
    async for event in agent.run(
        prompt="Create and test main.py",
        workspace=ws,
        session_id="s1",
        run_id="r1",
    ):
        events.append(event)

    types = [e.type for e in events]
    assert EventType.TOOL_STARTED in types
    assert EventType.TOOL_COMPLETED in types
    assert EventType.FILE_CREATED in types
    assert EventType.EXECUTION_OUTPUT in types
    assert EventType.AGENT_COMPLETED in types

    # Verify tool call message ordering in recorded provider calls:
    # After step 1: expect assistant tool_calls message, then tool message
    call2 = mock_llm.recorded_calls[1]
    history = call2["messages"]
    roles = [m["role"] for m in history]

    # Look for assistant followed immediately by tool
    asst_idx = None
    for i, r in enumerate(roles):
        if r == "assistant" and "tool_calls" in history[i]:
            asst_idx = i
            break
    assert asst_idx is not None
    assert roles[asst_idx + 1] == "tool"
    assert history[asst_idx + 1]["tool_call_id"] == "call_write_1"


@pytest.mark.asyncio
async def test_agent_multi_tool_calls_in_single_response(test_env):
    ws, mock_llm, agent = test_env

    # Single response returns two tool calls at once
    mock_llm.queue_multi_tool_calls(
        [
            ("write_file", {"file_path": "a.txt", "content": "A"}),
            ("write_file", {"file_path": "b.txt", "content": "B"}),
        ]
    )
    mock_llm.queue_text("Both files written.")

    events = []
    async for event in agent.run(
        prompt="Write a and b",
        workspace=ws,
        session_id="s1",
        run_id="r1",
    ):
        events.append(event)

    created_files = [e.data.get("path") for e in events if e.type == EventType.FILE_CREATED]
    assert "a.txt" in created_files
    assert "b.txt" in created_files


@pytest.mark.asyncio
async def test_agent_auto_fix_on_error(test_env):
    ws, mock_llm, agent = test_env

    # 1. Write broken code
    mock_llm.queue_tool_call(
        name="write_file",
        arguments={"file_path": "broken.py", "content": "raise ValueError('oops')"},
    )
    # 2. Run broken code -> produces execution error
    mock_llm.queue_tool_call(
        name="run_code",
        arguments={"path": "broken.py"},
    )
    # 3. Model sees auto-fix message and fixes with edit_file
    mock_llm.queue_tool_call(
        name="edit_file",
        arguments={
            "file_path": "broken.py",
            "old_content": "raise ValueError('oops')",
            "new_content": "print('fixed')",
        },
    )
    # 4. Final text
    mock_llm.queue_text("Bug fixed!")

    events = []
    async for event in agent.run(
        prompt="Fix the code",
        workspace=ws,
        session_id="s1",
        run_id="r1",
    ):
        events.append(event)

    types = [e.type for e in events]
    assert EventType.FILE_MODIFIED in types
    assert EventType.AGENT_COMPLETED in types


@pytest.mark.asyncio
async def test_agent_cancellation(test_env):
    ws, mock_llm, agent = test_env

    cancel_event = asyncio.Event()

    # Queue a tool call
    mock_llm.queue_tool_call(
        name="write_file",
        arguments={"file_path": "foo.txt", "content": "bar"},
    )

    # Trigger cancellation before second step
    cancel_event.set()

    events = []
    async for event in agent.run(
        prompt="Do work",
        workspace=ws,
        session_id="s1",
        run_id="r1",
        cancellation_event=cancel_event,
    ):
        events.append(event)

    types = [e.type for e in events]
    assert EventType.AGENT_CANCELLED in types
    assert EventType.AGENT_COMPLETED not in types


@pytest.mark.asyncio
async def test_agent_model_failure(test_env):
    ws, mock_llm, agent = test_env

    mock_llm.queue_response(LLMResponse(error="Authentication failure: invalid API key"))

    events = []
    async for event in agent.run(
        prompt="Test failure",
        workspace=ws,
        session_id="s1",
        run_id="r1",
    ):
        events.append(event)

    types = [e.type for e in events]
    assert EventType.AGENT_FAILED in types
    assert "Authentication failure" in events[-1].data["error"]
