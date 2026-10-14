"""Automated tests for FastAPI endpoints, projects, sessions, agent runs, and WebSockets."""

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.api.run_manager import run_manager
from src.db.database import Database, db
from src.llm.mock_provider import MockLLMProvider


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path):
    """Point the shared Database singleton at a temporary file for full test isolation."""
    fresh = Database(db_path=tmp_path / "test.db")
    db.db_path = fresh.db_path
    db._init_db()
    yield


@pytest.fixture(autouse=True)
def setup_mock_llm(tmp_path: Path):
    # Setup temporary mock provider and isolated db
    mock = MockLLMProvider()
    run_manager.set_provider(mock)
    return mock


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
async def test_project_crud_and_files():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project
        create_res = await client.post(
            "/api/projects", json={"name": "Test Project", "description": "Demo"}
        )
        assert create_res.status_code == 201
        project = create_res.json()
        project_id = project["id"]
        assert project["name"] == "Test Project"

        # List projects
        list_res = await client.get("/api/projects")
        assert list_res.status_code == 200
        assert any(p["id"] == project_id for p in list_res.json())

        # Write a file via file content PUT
        put_file = await client.put(
            f"/api/projects/{project_id}/files/content",
            json={"path": "src/index.js", "content": "console.log('hello');"},
        )
        assert put_file.status_code == 200

        # Read back file content
        get_file = await client.get(
            f"/api/projects/{project_id}/files/content",
            params={"path": "src/index.js"},
        )
        assert get_file.status_code == 200
        assert "console.log('hello');" in get_file.json()["content"]

        # List files in workspace
        files_res = await client.get(f"/api/projects/{project_id}/files")
        assert files_res.status_code == 200
        file_paths = [f["path"] for f in files_res.json()["files"]]
        assert "src/index.js" in file_paths

        # Delete project
        del_res = await client.delete(f"/api/projects/{project_id}")
        assert del_res.status_code == 200
        assert del_res.json()["deleted"] is True


@pytest.mark.asyncio
async def test_git_import_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid protocol: file://
        res1 = await client.post(
            "/api/projects/import-git",
            json={"name": "Bad Protocol", "git_url": "file:///etc/passwd"},
        )
        assert res1.status_code == 400
        assert "Only public HTTP and HTTPS" in res1.json()["detail"]

        # Loopback/private IP prohibited
        res2 = await client.post(
            "/api/projects/import-git",
            json={"name": "Bad Host", "git_url": "http://127.0.0.1:8000/repo.git"},
        )
        assert res2.status_code == 400
        assert "prohibited" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_session_management():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project first
        proj = (await client.post("/api/projects", json={"name": "Session Test"})).json()
        project_id = proj["id"]

        # Create session
        sess_res = await client.post(
            "/api/sessions",
            json={"project_id": project_id, "title": "Debug Session"},
        )
        assert sess_res.status_code == 201
        session_id = sess_res.json()["id"]

        # Retrieve session
        get_sess = await client.get(f"/api/sessions/{session_id}")
        assert get_sess.status_code == 200
        assert get_sess.json()["session"]["title"] == "Debug Session"

        # List project sessions
        list_sess = await client.get(f"/api/projects/{project_id}/sessions")
        assert list_sess.status_code == 200
        assert any(s["id"] == session_id for s in list_sess.json())


@pytest.mark.asyncio
async def test_agent_run_lifecycle(setup_mock_llm: MockLLMProvider):
    setup_mock_llm.queue_text("Agent response for API test.")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project and session
        proj = (await client.post("/api/projects", json={"name": "Run Test"})).json()
        project_id = proj["id"]
        default_sess = proj.get("default_session_id")

        # Start run
        run_res = await client.post(
            "/api/agent/runs",
            json={
                "project_id": project_id,
                "session_id": default_sess,
                "prompt": "Hello agent",
            },
        )
        assert run_res.status_code == 202
        run_id = run_res.json()["run_id"]

        # Wait briefly for background execution to complete
        for _ in range(20):
            await asyncio.sleep(0.05)
            status_res = await client.get(f"/api/agent/runs/{run_id}")
            if status_res.json()["status"] in ("completed", "failed", "cancelled"):
                break

        final_run = (await client.get(f"/api/agent/runs/{run_id}")).json()
        assert final_run["status"] == "completed"

        # Check recorded events
        events = await db.get_run_events(run_id)
        assert len(events) >= 3
        event_types = [e["type"] for e in events]
        assert "agent.started" in event_types
        assert "agent.completed" in event_types


@pytest.mark.asyncio
async def test_agent_run_cancellation(setup_mock_llm: MockLLMProvider):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proj = (await client.post("/api/projects", json={"name": "Cancel Test"})).json()
        project_id = proj["id"]
        sess_id = proj.get("default_session_id")

        # Queue a tool call that writes a file
        setup_mock_llm.queue_tool_call(
            name="write_file",
            arguments={"file_path": "slow.txt", "content": "slow work"},
        )

        run_res = await client.post(
            "/api/agent/runs",
            json={
                "project_id": project_id,
                "session_id": sess_id,
                "prompt": "Do slow work",
            },
        )
        run_id = run_res.json()["run_id"]

        # Cancel immediately
        cancel_res = await client.post(f"/api/agent/runs/{run_id}/cancel")
        assert cancel_res.status_code == 200
        assert cancel_res.json()["cancelled"] is True


def test_websocket_streaming_and_replay():
    import json

    from starlette.testclient import TestClient

    client = TestClient(app)

    # 1. Seed project, session, run, and events in database
    import asyncio

    async def seed():
        await db.create_project("ws_proj", "WS Test", "/tmp/ws_test")
        await db.create_session("ws_sess", "ws_proj", "WS Session")
        await db.create_run("run_ws_1", "ws_sess", "ws_proj", "prompt")
        await db.record_event("run_ws_1", 1, "agent.started", {"step": 1})
        await db.record_event("run_ws_1", 2, "agent.message", {"content": "Hello via WS"})
        await db.update_run_status("run_ws_1", "completed")

    asyncio.run(seed())

    # 3. Reconnect with since=1 — only the agent.message event should replay
    with client.websocket_connect("/api/agent/runs/run_ws_1/events?since=1") as ws:
        replayed = json.loads(ws.receive_text())
        assert replayed["type"] == "agent.message"
        assert replayed["sequence"] == 2

    with pytest.raises(Exception):
        # since=2 filters out everything; connection should be closed with no events
        with client.websocket_connect("/api/agent/runs/run_ws_1/events?since=2") as ws:
            ws.receive_text()

    # 2. Connect via WebSocket and verify replay of events
    with client.websocket_connect("/api/agent/runs/run_ws_1/events?since=0") as ws:
        ev1 = json.loads(ws.receive_text())
        assert ev1["type"] == "agent.started"
        assert ev1["sequence"] == 1

        ev2 = json.loads(ws.receive_text())
        assert ev2["type"] == "agent.message"
        assert ev2["data"]["content"] == "Hello via WS"
