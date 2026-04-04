"""CodeCrafter Configuration.

All settings are centralized here for easy customization.
"""

import os

# =============================================================================
# General
# =============================================================================

VERSION = "3.1.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# Directory Configuration
# =============================================================================

PROJECT_FOLDER_NAME = "workspace"
WORKING_DIR = os.path.join(BASE_DIR, PROJECT_FOLDER_NAME)
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")

# =============================================================================
# Session Configuration
# =============================================================================

MAX_SESSION_MESSAGES = 30
SESSION_FILE_EXTENSION = ".json"
CORRUPT_EXTENSION = ".corrupt"
SESSION_PREFIX = "session_"
SESSION_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"

# =============================================================================
# Model Configuration (Ollama Cloud)
# =============================================================================

OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "qwen3.5:cloud"

# Model shortcuts for --model flag
MODELS = {
    "qwen3.5": "qwen3.5:cloud",
    "qwen3-coder": "qwen3-coder-next:cloud",
    "nemotron-super": "nemotron-3-super:cloud",
}

# Fallback model chain — ordered by preference
FALLBACK_MODELS = [
    "qwen3.5:cloud",
    "qwen3-coder-next:cloud",
    "nemotron-3-super:cloud",
]

MAX_TOKENS = 4096

# =============================================================================
# Agent Loop Configuration
# =============================================================================

MAX_AGENT_STEPS = 25
MAX_AUTO_FIX = 3

# Context trimming — trigger trim when messages exceed this count.
# Must be significantly larger than CONTEXT_KEEP_MESSAGES to be effective.
CONTEXT_TRIM_THRESHOLD = 12
CONTEXT_KEEP_MESSAGES = 6

# =============================================================================
# UI Configuration
# =============================================================================

SPINNER_FRAME_DURATION = 0.12
SPINNER_WORD_SWITCH_INTERVAL = 6.0

SPINNER_WORDS = [
    "thinking ",
    "analyzing ",
    "building ",
    "crafting ",
    "processing ",
    "resolving ",
    "computing ",
    "generating ",
    "compiling ",
    "synthesizing ",
    "optimizing ",
    "evaluating ",
    "reasoning ",
    "assembling ",
    "mapping ",
    "parsing ",
    "loading ",
    "scanning ",
    "indexing ",
    "decoding ",
    "linking ",
    "patching ",
    "tracing ",
    "wiring ",
    "forging ",
    "hashing ",
    "querying ",
    "rendering ",
    "buffering ",
    "streaming ",
    "iterating ",
    "traversing ",
    "encoding ",
    "deploying ",
    "profiling ",
    "debugging ",
    "refactoring ",
    "architecting ",
    "bootstrapping ",
    "calibrating ",
]

SPINNER_FRAMES = ["󰚔", "󰚕", "󰚖", "󰚗", "󰚘", "󰚙"]

# =============================================================================
# Display Configuration
# =============================================================================

VERBOSE_TRUNCATE_LENGTH = 150
VERBOSE_MAX_LINES = 3
BANNER_WIDTH = 52

# =============================================================================
# Error Detection Patterns
# =============================================================================

EXECUTION_ERROR_INDICATORS = [
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

TIMEOUT_INDICATOR = "timed out"

FALLBACK_TRIGGERS = ["429", "rate_limit", "503", "unavailable", "overloaded", "not found"]

# =============================================================================
# Identity
# =============================================================================

DEFAULT_USER_NAME = "Developer"
AGENT_NAME = "CodeCrafter"
