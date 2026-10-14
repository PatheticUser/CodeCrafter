"""Central application settings via Pydantic Settings."""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class WorkspaceBackend(StrEnum):
    """Workspace execution backend."""

    LOCAL = "local"
    DOCKER = "docker"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App Metadata ──────────────────────────────────────────────────────
    APP_NAME: str = "CodeCrafter"
    APP_VERSION: str = "3.0.0"
    APP_ENV: Environment = Environment.DEVELOPMENT
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    # Base directory (project root)
    BASE_DIR: Path = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent

    # ── LLM Configuration ─────────────────────────────────────────────────
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: float = 120.0
    LLM_MAX_RETRIES: int = 3
    LLM_TEMPERATURE: float | None = 0.2
    MAX_TOKENS: int = 8192

    # ── Workspace Configuration ───────────────────────────────────────────
    WORKSPACE_BACKEND: WorkspaceBackend = WorkspaceBackend.LOCAL
    WORKSPACE_ROOT: Path | None = None
    WORKSPACE_COMMAND_TIMEOUT: int = 60
    WORKSPACE_CONTAINER_IMAGE: str = "python:3.11-slim"
    WORKSPACE_MAX_OUTPUT_BYTES: int = 50000
    WORKSPACE_MAX_FILE_BYTES: int = 5 * 1024 * 1024  # 5 MB

    @property
    def workspace_root_dir(self) -> Path:
        """Root directory housing all project workspaces."""
        if self.WORKSPACE_ROOT:
            return self.WORKSPACE_ROOT
        return self.BASE_DIR / "workspace"

    # ── Persistence & Database ────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./data/codecrafter.db"

    @property
    def sqlite_db_path(self) -> Path:
        """Extract filesystem path from sqlite URL."""
        if self.DATABASE_URL.startswith("sqlite:///"):
            raw_path = self.DATABASE_URL.removeprefix("sqlite:///")
            if raw_path.startswith("./"):
                return self.BASE_DIR / raw_path[2:]
            return Path(raw_path)
        return self.BASE_DIR / "data" / "codecrafter.db"

    # ── Security & Networking ─────────────────────────────────────────────
    API_TOKEN: str = ""
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # ── Agent Loop Limits ─────────────────────────────────────────────────
    MAX_AGENT_STEPS: int = 25
    MAX_AUTO_FIX: int = 3
    CONTEXT_TRIM_THRESHOLD: int = 6
    MAX_TREE_ITEMS: int = 50

    # ── Legacy & UI Configuration ─────────────────────────────────────────
    DEFAULT_USER_NAME: str = "Developer"
    AGENT_NAME: str = "CodeCrafter"
    FILE_MUTATING_TOOLS: set[str] = {"write_file", "edit_file", "delete_file", "run_command"}

    EXECUTION_ERROR_INDICATORS: list[str] = [
        "Traceback (most recent",
        "SyntaxError",
        "NameError",
        "TypeError",
        "ValueError",
        "ImportError",
        "ModuleNotFoundError",
        "FileNotFoundError",
        "IndentationError",
        "AttributeError",
        "KeyError",
        "IndexError",
        "Compilation failed",
        "EXIT CODE: 1",
        "EXIT CODE: 2",
    ]
    TIMEOUT_INDICATOR: str = "timed out"

    # Legacy session compatibility
    SESSION_PREFIX: str = "session_"
    SESSION_TIMESTAMP_FORMAT: str = "%Y-%m-%d_%H-%M-%S"
    SESSION_FILE_EXTENSION: str = ".json"
    CORRUPT_EXTENSION: str = ".corrupt"
    MAX_SESSION_MESSAGES: int = 50

    @property
    def sessions_dir(self) -> Path:
        return self.BASE_DIR / "sessions"


settings = Settings()
