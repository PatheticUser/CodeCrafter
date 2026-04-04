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

# Working directory - Change this to point to your target project
# Default: "workspace" folder in the same directory as this file
PROJECT_FOLDER_NAME = "workspace"
WORKING_DIR = os.path.join(BASE_DIR, PROJECT_FOLDER_NAME)

# Session storage (outside workspace so it doesn't pollute user files)
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")

# Functions directory
FUNCTIONS_DIR = os.path.join(BASE_DIR, "functions")

# =============================================================================
# Session Configuration
# =============================================================================

# Maximum messages to keep in session history
MAX_SESSION_MESSAGES = 30

# Session file extension
SESSION_FILE_EXTENSION = ".json"

# Corrupted session backup extension
CORRUPT_EXTENSION = ".corrupt"

# Session filename prefix
SESSION_PREFIX = "session_"

# Session filename datetime format
SESSION_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"

# =============================================================================
# Model Configuration (Ollama Cloud)
# =============================================================================

# Ollama API endpoint
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# Default model
DEFAULT_MODEL = "qwen3.5:cloud"

# Available models for --model flag shortcuts
MODELS = {
    "qwen3.5": "qwen3.5:cloud",
    "qwen3-coder": "qwen3-coder-next:cloud",
    "nemotron-super": "nemotron-3-super:cloud",
}

# Fallback model chain — ordered by preference.
# When the active model fails, CodeCrafter tries the next one automatically.
# All models must support tool/function calling.
FALLBACK_MODELS = [
    "qwen3.5:cloud",              # Primary: strong all-rounder with tool + vision + thinking
    "qwen3-coder-next:cloud",     # Coding-focused, agentic workflows
    "nemotron-3-super:cloud",     # NVIDIA 120B MoE, strong reasoning
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

# Context trimming threshold (number of messages before trimming)
CONTEXT_TRIM_THRESHOLD = 6

# Number of messages to keep when trimming
CONTEXT_KEEP_MESSAGES = 6

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

SPINNER_FRAMES = ["󰚔", "󰚕", "󰚖", "󰚗", "󰚘", "󰚙"]

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
