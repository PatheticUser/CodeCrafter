import os

# =============================================================================
# CodeCrafter Configuration
# =============================================================================

# Version
VERSION = "3.0.0"

# Base directory (root of the project)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# Directory Configuration
# =============================================================================

# Working directory - defaults to the sandboxed workspace/
# Override via CODECRAFTER_WORKING_DIR env var or --path CLI flag
WORKING_DIR = os.environ.get("CODECRAFTER_WORKING_DIR") or os.path.join(BASE_DIR, "workspace")

# =============================================================================
# Model Configuration (Ollama Cloud)
# =============================================================================

# Ollama API endpoint
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# Default model
DEFAULT_MODEL = "gpt-oss:120b-cloud"

# Available models for --model flag shortcuts
MODELS = {
    "gpt-oss": "gpt-oss:120b-cloud",
    "nemotron-super": "nemotron-3-super:cloud",
}

# Fallback model chain — ordered by preference.
# When the active model fails, CodeCrafter tries the next one automatically.
# All models must support tool/function calling.
FALLBACK_MODELS = [
    "gpt-oss:120b-cloud",
    "nemotron-3-super:cloud",
]

# Token limits
MAX_TOKENS = 4096

# =============================================================================
# Agent Loop Configuration
# =============================================================================

# Maximum steps per user turn
MAX_AGENT_STEPS = 25

# Maximum auto-fix attempts per user turn
MAX_AUTO_FIX = 3

# Context trimming threshold (exchanges to keep in history)
CONTEXT_TRIM_THRESHOLD = 6

# Maximum items in workspace tree display (prevents context overflow)
MAX_TREE_ITEMS = 50

# =============================================================================
# UI Configuration
# =============================================================================

# Spinner animation settings
SPINNER_FRAME_DURATION = 0.12  # seconds between frames
SPINNER_WORD_SWITCH_INTERVAL = 6.0  # seconds before switching words

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

SPINNER_FRAMES = ["◐", "◓", "◑", "◒"]

# =============================================================================
# Display Configuration
# =============================================================================

# Verbose output settings
VERBOSE_TRUNCATE_LENGTH = 150  # Max length for verbose result display
VERBOSE_MAX_LINES = 3  # Max lines for verbose result display

# Banner width (characters)
BANNER_WIDTH = 52

# =============================================================================
# File Operation Settings
# =============================================================================

# File-mutating tools that trigger workspace refresh
FILE_MUTATING_TOOLS = {"write_file", "edit_file", "delete_file", "run_command"}

# =============================================================================
# Error Detection Patterns
# =============================================================================

# Execution error indicators that trigger auto-fix
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

# Timeout indicator (not auto-fixable)
TIMEOUT_INDICATOR = "timed out"

# Error patterns that trigger model fallback
FALLBACK_TRIGGERS = ["429", "rate_limit", "503", "unavailable", "overloaded", "not found"]

# =============================================================================
# Default Values
# =============================================================================

# Default user name
DEFAULT_USER_NAME = "Developer"

# Agent name display
AGENT_NAME = "CodeCrafter"
