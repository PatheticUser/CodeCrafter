"""Configuration adapter preserving backwards compatibility with src.core.settings."""

import os
from src.core.settings import settings

VERSION = settings.APP_VERSION
BASE_DIR = str(settings.BASE_DIR)
WORKING_DIR = str(settings.workspace_root_dir)

# Model configuration
DEFAULT_MODEL = settings.LLM_MODEL
MODELS = {
    "default": settings.LLM_MODEL,
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4o": "gpt-4o",
}
FALLBACK_MODELS = [settings.LLM_MODEL]
MAX_TOKENS = settings.MAX_TOKENS

# Agent configuration
MAX_AGENT_STEPS = settings.MAX_AGENT_STEPS
MAX_AUTO_FIX = settings.MAX_AUTO_FIX
CONTEXT_TRIM_THRESHOLD = settings.CONTEXT_TRIM_THRESHOLD
MAX_TREE_ITEMS = settings.MAX_TREE_ITEMS

# Error patterns
EXECUTION_ERROR_INDICATORS = settings.EXECUTION_ERROR_INDICATORS
TIMEOUT_INDICATOR = settings.TIMEOUT_INDICATOR
FALLBACK_TRIGGERS = ["429", "rate_limit", "503", "unavailable", "overloaded", "not found"]
FILE_MUTATING_TOOLS = settings.FILE_MUTATING_TOOLS

# UI
DEFAULT_USER_NAME = settings.DEFAULT_USER_NAME
AGENT_NAME = settings.AGENT_NAME
SPINNER_FRAME_DURATION = 0.12
SPINNER_WORD_SWITCH_INTERVAL = 6.0
SPINNER_WORDS = ["thinking ", "building ", "crafting ", "testing "]
SPINNER_FRAMES = ["◐", "◓", "◑", "◒"]
BANNER_WIDTH = 52
VERBOSE_TRUNCATE_LENGTH = 150
VERBOSE_MAX_LINES = 3
