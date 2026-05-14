"""Application settings using Pydantic Settings v2.

All configuration flows through a single validated settings object.
Reads from .env file and environment variables.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import ClassVar

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from .env / environment variables.

    Every configurable value lives here as a typed field with a default.
    Grouped logically: app metadata, Ollama config, agent behavior, paths, UI.
    """

    # ── App Metadata ──────────────────────────────────────────────────────

    APP_NAME: str = "CodeCrafter"
    APP_VERSION: str = "3.0.0"
    APP_ENV: Environment = Environment.DEVELOPMENT

    # ── Paths ─────────────────────────────────────────────────────────────

    BASE_DIR: Path = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent

    @property
    def workspace_dir(self) -> Path:
        """Sandboxed working directory for user files."""
        return self.BASE_DIR / "workspace"

    @property
    def sessions_dir(self) -> Path:
        """Directory for JSON session persistence."""
        return self.BASE_DIR / "sessions"

    # ── Ollama / LLM Configuration ────────────────────────────────────────

    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    DEFAULT_MODEL: str = "qwen3.5:cloud"

    # Model shortcut aliases for --model flag
    MODELS: dict[str, str] = {
        "qwen3.5": "qwen3.5:cloud",
        "qwen3-coder": "qwen3-coder-next:cloud",
        "nemotron-super": "nemotron-3-super:cloud",
    }

    # Fallback chain — ordered by preference. All must support tool calling.
    FALLBACK_MODELS: list[str] = [
        "qwen3.5:cloud",
        "qwen3-coder-next:cloud",
        "nemotron-3-super:cloud",
    ]

    # Token limits
    MAX_TOKENS: int = 4096

    # Future auth / secrets
    # JWT_SECRET: SecretStr = SecretStr("change-me")
    # DB_URL: str = ""

    # ── Agent Loop Configuration ──────────────────────────────────────────

    MAX_AGENT_STEPS: int = 25
    MAX_AUTO_FIX: int = 3
    CONTEXT_TRIM_THRESHOLD: int = 6

    # ── Session Configuration ─────────────────────────────────────────────

    MAX_SESSION_MESSAGES: int = 30
    SESSION_FILE_EXTENSION: str = ".json"
    CORRUPT_EXTENSION: str = ".corrupt"
    SESSION_PREFIX: str = "session_"
    SESSION_TIMESTAMP_FORMAT: str = "%Y-%m-%d_%H-%M-%S"

    # ── UI Configuration ──────────────────────────────────────────────────

    SPINNER_FRAME_DURATION: float = 0.12
    SPINNER_WORD_SWITCH_INTERVAL: float = 6.0
    SPINNER_WORDS: list[str] = [
        "thinking ", "analyzing ", "building ", "crafting ",
        "processing ", "resolving ", "computing ", "generating ",
        "compiling ", "synthesizing ", "optimizing ", "evaluating ",
        "reasoning ", "assembling ", "mapping ", "parsing ",
        "loading ", "scanning ", "indexing ", "decoding ",
        "linking ", "patching ", "tracing ", "wiring ",
        "forging ", "hashing ", "querying ", "rendering ",
        "buffering ", "streaming ", "iterating ", "traversing ",
        "encoding ", "deploying ", "profiling ", "debugging ",
        "refactoring ", "architecting ", "bootstrapping ", "calibrating ",
    ]
    SPINNER_FRAMES: list[str] = ["\U000f0698", "\U000f0699", "\U000f069a", "\U000f069b", "\U000f069c", "\U000f069d"]

    # ── Display Configuration ─────────────────────────────────────────────

    VERBOSE_TRUNCATE_LENGTH: int = 150
    VERBOSE_MAX_LINES: int = 3
    BANNER_WIDTH: int = 52

    # ── File Operation Settings ───────────────────────────────────────────

    FILE_MUTATING_TOOLS: set[str] = {"write_file", "edit_file", "delete_file", "run_command"}

    # ── Error Detection Patterns ──────────────────────────────────────────

    EXECUTION_ERROR_INDICATORS: list[str] = [
        "Traceback (most recent",
        "SyntaxError", "NameError", "TypeError", "ValueError",
        "ImportError", "ModuleNotFoundError", "FileNotFoundError",
        "IndentationError", "AttributeError", "KeyError", "IndexError",
        "Compilation failed", "EXIT CODE: 1", "EXIT CODE: 2",
    ]
    TIMEOUT_INDICATOR: str = "timed out"
    FALLBACK_TRIGGERS: list[str] = [
        "429", "rate_limit", "503", "unavailable", "overloaded", "not found",
    ]

    # ── User Configuration ────────────────────────────────────────────────

    DEFAULT_USER_NAME: str = "Developer"
    AGENT_NAME: str = "CodeCrafter"

    # ── Pydantic config ───────────────────────────────────────────────────

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Singleton — import this everywhere instead of instantiating Settings.
settings = Settings()
