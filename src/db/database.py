"""SQLite persistence layer for projects, sessions, messages, runs, and events."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core.settings import settings


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    """Thread-safe SQLite database manager."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or settings.sqlite_db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                workspace_path TEXT NOT NULL,
                git_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL,
                finished_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS previews (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                run_id TEXT,
                status TEXT NOT NULL DEFAULT 'stopped',
                port INTEGER,
                container_id TEXT,
                framework TEXT,
                started_at TEXT,
                stopped_at TEXT,
                url_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_runs_session ON runs(session_id);
            CREATE INDEX IF NOT EXISTS idx_previews_project ON previews(project_id);
            CREATE INDEX IF NOT EXISTS idx_previews_status ON previews(status);
            """)

    # ── Projects ──────────────────────────────────────────────────────────────

    async def create_project(
        self,
        project_id: str,
        name: str,
        workspace_path: str,
        description: str = "",
        git_url: str | None = None,
    ) -> dict[str, Any]:
        now = _utc_now()

        def _run():
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO projects
                        (id, name, description, workspace_path, git_url, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (project_id, name, description, workspace_path, git_url, now, now),
                )
            return {
                "id": project_id,
                "name": name,
                "description": description,
                "workspace_path": workspace_path,
                "git_url": git_url,
                "created_at": now,
                "updated_at": now,
            }

        return await asyncio.to_thread(_run)

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        def _run():
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
                row = cur.fetchone()
                return dict(row) if row else None

        return await asyncio.to_thread(_run)

    async def list_projects(self) -> list[dict[str, Any]]:
        def _run():
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC")
                return [dict(r) for r in cur.fetchall()]

        return await asyncio.to_thread(_run)

    async def delete_project(self, project_id: str) -> bool:
        def _run():
            with self._get_connection() as conn:
                cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
                return cur.rowcount > 0

        return await asyncio.to_thread(_run)

    # ── Sessions ──────────────────────────────────────────────────────────────

    async def create_session(
        self, session_id: str, project_id: str, title: str = "New Session"
    ) -> dict[str, Any]:
        now = _utc_now()

        def _run():
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO sessions (id, project_id, title, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (session_id, project_id, title, now, now),
                )
            return {
                "id": session_id,
                "project_id": project_id,
                "title": title,
                "created_at": now,
                "updated_at": now,
            }

        return await asyncio.to_thread(_run)

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        def _run():
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
                row = cur.fetchone()
                return dict(row) if row else None

        return await asyncio.to_thread(_run)

    async def list_sessions(self, project_id: str) -> list[dict[str, Any]]:
        def _run():
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM sessions WHERE project_id = ? ORDER BY updated_at DESC",
                    (project_id,),
                )
                return [dict(r) for r in cur.fetchall()]

        return await asyncio.to_thread(_run)

    # ── Messages ──────────────────────────────────────────────────────────────

    async def add_message(
        self,
        message_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _utc_now()
        meta_json = json.dumps(metadata) if metadata else None

        def _run():
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO messages (id, session_id, role, content, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (message_id, session_id, role, content, meta_json, now),
                )
                conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
            return {
                "id": message_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "created_at": now,
            }

        return await asyncio.to_thread(_run)

    async def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        def _run():
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
                    (session_id,),
                )
                res = []
                for row in cur.fetchall():
                    item = dict(row)
                    if item.get("metadata"):
                        try:
                            item["metadata"] = json.loads(item["metadata"])
                        except Exception:
                            item["metadata"] = {}
                    else:
                        item["metadata"] = {}
                    res.append(item)
                return res

        return await asyncio.to_thread(_run)

    # ── Runs ──────────────────────────────────────────────────────────────────

    async def create_run(
        self,
        run_id: str,
        session_id: str,
        project_id: str,
        prompt: str,
    ) -> dict[str, Any]:
        now = _utc_now()

        def _run():
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO runs (id, session_id, project_id, prompt, status, created_at)
                    VALUES (?, ?, ?, ?, 'pending', ?)
                    """,
                    (run_id, session_id, project_id, prompt, now),
                )
            return {
                "id": run_id,
                "session_id": session_id,
                "project_id": project_id,
                "prompt": prompt,
                "status": "pending",
                "created_at": now,
                "finished_at": None,
                "error": None,
            }

        return await asyncio.to_thread(_run)

    async def update_run_status(
        self,
        run_id: str,
        status: str,
        error: str | None = None,
    ) -> None:
        now = _utc_now()
        is_finished = status in ("completed", "failed", "cancelled")

        def _run():
            with self._get_connection() as conn:
                if is_finished:
                    conn.execute(
                        "UPDATE runs SET status = ?, error = ?, finished_at = ? WHERE id = ?",
                        (status, error, now, run_id),
                    )
                else:
                    conn.execute(
                        "UPDATE runs SET status = ?, error = ? WHERE id = ?",
                        (status, error, run_id),
                    )

        await asyncio.to_thread(_run)

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        def _run():
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
                row = cur.fetchone()
                return dict(row) if row else None

        return await asyncio.to_thread(_run)

    # ── Events ────────────────────────────────────────────────────────────────

    async def record_event(
        self,
        run_id: str,
        sequence: int,
        event_type: str,
        payload: dict[str, Any],
        timestamp: str | None = None,
    ) -> None:
        ts = timestamp or _utc_now()
        payload_json = json.dumps(payload)

        def _run():
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO events (run_id, sequence, event_type, payload, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (run_id, sequence, event_type, payload_json, ts),
                )

        await asyncio.to_thread(_run)

    async def get_run_events(self, run_id: str, since_sequence: int = 0) -> list[dict[str, Any]]:
        def _run():
            with self._get_connection() as conn:
                cur = conn.execute(
                    """
                    SELECT sequence, event_type, payload, timestamp
                    FROM events
                    WHERE run_id = ? AND sequence > ?
                    ORDER BY sequence ASC
                    """,
                    (run_id, since_sequence),
                )
                results = []
                for row in cur.fetchall():
                    try:
                        data = json.loads(row["payload"])
                    except Exception:
                        data = {}
                    results.append(
                        {
                            "type": row["event_type"],
                            "run_id": run_id,
                            "sequence": row["sequence"],
                            "timestamp": row["timestamp"],
                            "data": data,
                        }
                    )
                return results

        return await asyncio.to_thread(_run)

    # ── Previews ──────────────────────────────────────────────────────────────

    async def create_preview(
        self,
        preview_id: str,
        project_id: str,
        run_id: str | None,
        status: str = "stopped",
        port: int | None = None,
        container_id: str | None = None,
        framework: str | None = None,
        url_path: str | None = None,
    ) -> dict[str, Any]:
        now = _utc_now()

        def _run():
            with self._get_connection() as conn:
                conn.execute(
                    """INSERT INTO previews
                        (id, project_id, run_id, status, port,
                         container_id, framework, url_path, started_at, updated_at, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        preview_id,
                        project_id,
                        run_id,
                        status,
                        port,
                        container_id,
                        framework,
                        url_path,
                        now if status != "stopped" else None,
                        now,
                        now,
                    ),
                )
            return {
                "id": preview_id,
                "project_id": project_id,
                "run_id": run_id,
                "status": status,
                "port": port,
                "container_id": container_id,
                "framework": framework,
                "url_path": url_path,
                "started_at": now if status != "stopped" else None,
                "updated_at": now,
                "created_at": now,
            }

        return await asyncio.to_thread(_run)

    async def get_preview(self, preview_id: str) -> dict[str, Any] | None:
        def _run():
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM previews WHERE id = ?", (preview_id,))
                row = cur.fetchone()
                return dict(row) if row else None

        return await asyncio.to_thread(_run)

    async def list_previews(self, project_id: str) -> list[dict[str, Any]]:
        def _run():
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM previews WHERE project_id = ? ORDER BY started_at DESC",
                    (project_id,),
                )
                return [dict(r) for r in cur.fetchall()]

        return await asyncio.to_thread(_run)

    async def update_preview_status(
        self,
        preview_id: str,
        status: str,
        port: int | None = None,
        container_id: str | None = None,
    ) -> None:
        now = _utc_now()
        fields = ["status = ?", "updated_at = ?"]
        params = [status, now]
        if port is not None:
            fields.append("port = ?")
            params.append(port)
        if container_id is not None:
            fields.append("container_id = ?")
            params.append(container_id)
        params.append(preview_id)

        def _run():
            with self._get_connection() as conn:
                query = f"UPDATE previews SET {', '.join(fields)} WHERE id = ?"
                conn.execute(query, params)

        await asyncio.to_thread(_run)

    async def delete_preview(self, preview_id: str) -> bool:
        def _run():
            with self._get_connection() as conn:
                cur = conn.execute("DELETE FROM previews WHERE id = ?", (preview_id,))
                return cur.rowcount > 0

        return await asyncio.to_thread(_run)


db = Database()
