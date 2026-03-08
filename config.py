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
# Model Configuration
# =============================================================================

# Available Models
MODELS = {
    "qwen3-32b": "qwen/qwen3-32b",
    "llama-3.3-70b": "llama-3.3-70b-versatile",
    "llama-4-scout": "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.1-8b": "llama-3.1-8b-instant",
}

# Default model
DEFAULT_MODEL = "qwen3-32b"

# API Configuration
API_KEYS_FILE = "api_keys.json"
MAX_API_RETRIES = 3

# Token limits
MAX_TOKENS = 16384

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
    "thinking",
    "analyzing",
    "building",
    "crafting",
    "processing",
    "resolving",
    "computing",
    "generating",
    "compiling",
    "synthesizing",
    "optimizing",
    "evaluating",
    "reasoning",
    "assembling",
    "mapping",
    "parsing",
    "loading",
    "scanning",
    "indexing",
    "decoding",
    "linking",
    "patching",
    "tracing",
    "wiring",
    "forging",
    "hashing",
    "querying",
    "rendering",
    "buffering",
    "streaming",
    "iterating",
    "traversing",
    "encoding",
    "deploying",
    "profiling",
    "debugging",
    "refactoring",
    "architecting",
    "bootstrapping",
    "calibrating",
]

SPINNER_FRAMES = ["󰪞", "󰪟", "󰪠", "󰪡", "󰪢", "󰪣", "󰪤", "󰪥"]

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

# Project description file settings (legacy, kept for compatibility)
PROJECT_DESCRIPTION_FILE = "project_description.json"
AUTO_UPDATE_DESCRIPTION = True  # Set to False to disable auto-updates

# =============================================================================
# Error Detection Patterns
# =============================================================================

# Python error indicators that trigger auto-fix
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

# =============================================================================
# API Error Codes
# =============================================================================

# Rate limit error
RATE_LIMIT_ERROR = "429"
RATE_LIMIT_KEYWORD = "rate_limit"

# Invalid request / bad request
BAD_REQUEST_ERROR = "400"
INVALID_KEYWORD = "invalid"

# Service unavailable
SERVICE_UNAVAILABLE_ERROR = "503"
UNAVAILABLE_KEYWORD = "unavailable"

# Model decommissioned indicators
MODEL_DECOMMISSIONED_INDICATORS = ["decommissioned", "not found"]

# =============================================================================
# Default Values
# =============================================================================

# Default user name
DEFAULT_USER_NAME = "Developer"

# Agent name display
AGENT_NAME = "CodeCrafter"
