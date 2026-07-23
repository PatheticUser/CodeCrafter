"""Display and UI functions for CodeCrafter — Claude Code-inspired clean design."""

import os
import re
import shutil

from config import (
    VERSION,
    AGENT_NAME,
    VERBOSE_TRUNCATE_LENGTH,
    VERBOSE_MAX_LINES,
    DEFAULT_USER_NAME,
)


# ── Terminal width ──────────────────────────────────────────────────────

def terminal_width() -> int:
    """Return the current terminal width (default 80)."""
    return shutil.get_terminal_size((80, 20)).columns


# ── Colour / style helpers ──────────────────────────────────────────────

class Colors:
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def c(text: str, color: str) -> str:
    """Apply colour to text."""
    return f"{color}{text}{Colors.RESET}"


def dim(text: str) -> str:
    """Apply dim/grey styling."""
    return c(text, Colors.DIM)


def bold(text: str) -> str:
    """Apply bold styling."""
    return c(text, Colors.BOLD)


# ── Status icons (simple ASCII/Unicode, like Claude Code) ───────────────

class Icons:
    SUCCESS = "✓"
    ERROR = "✗"
    WARNING = "⚠"
    INFO = "ℹ"
    PROMPT = "▶"
    ARROW = "▸"
    ARROW_RIGHT = "→"
    BULLET = "•"
    CODE = "λ"
    FILE = "📄"
    FOLDER = "📁"
    WRITE = "✎"
    EDIT = "✏"
    DELETE = "✕"
    SEARCH = "🔍"
    GEAR = "⚙"
    PLAY = "▶"
    STOP = "■"
    TOKENS = "∑"
    BRAIN = "◆"
    TIME = "⏱"
    AGENT = "◆"
    FIX = "♺"
    DEBUG = "🐛"
    DIVIDER = "─"
    ELLIPSIS = "…"


# ── Action deduplication ────────────────────────────────────────────────

_shown_actions: list[str] = []


def reset_action_tracker():
    global _shown_actions
    _shown_actions = []


# ── Markdown stripping ─────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """Remove markdown formatting that doesn't render in terminals."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\*{3,}$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "  ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "  ", text, flags=re.MULTILINE)
    text = re.sub(r"^```\w*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Screen ──────────────────────────────────────────────────────────────

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


# ── Intro banner (minimal, Claude Code-inspired) ────────────────────────

def show_intro_banner(user_name: str, model_name: str = ""):
    """Startup banner."""
    clear_screen()
    print()
    print(f"  {c(AGENT_NAME, Colors.CYAN)}{bold(f' v{VERSION}')}  {dim(Icons.DIVIDER)}  {dim('AI coding assistant')}")
    print(f"  {dim(Icons.DIVIDER * 48)}")
    print(f"  {c(Icons.BULLET, Colors.DIM)}  {dim('Model:')} {c(model_name, Colors.CYAN)}")
    print(f"  {dim(Icons.BULLET)}  {dim('Type')} {c('help', Colors.YELLOW)} {dim('for commands —')} {c('exit', Colors.YELLOW)} {dim('to quit')}")
    print()
    print(f"  {c(Icons.SUCCESS, Colors.GREEN)}  {bold('Hello')}, {c(user_name, Colors.MAGENTA)} — ready when you are")
    print()


# ── Exit banner ─────────────────────────────────────────────────────────

def show_exit_banner(user_name: str):
    """Minimal exit message."""
    print()
    print(f"  {dim(Icons.DIVIDER * 48)}")
    print(f"  {c(Icons.STOP, Colors.RED)}  {bold('Goodbye')}  {dim(Icons.BULLET)}  {dim('See you,')} {c(user_name, Colors.MAGENTA)}")
    print(f"  {dim(Icons.DIVIDER * 48)}")
    print()


# ── Verbose mode ────────────────────────────────────────────────────────

def show_verbose_config(working_dir: str, auto_update: bool):
    print()
    print(f"  {c(Icons.DEBUG, Colors.YELLOW)}  {bold('Verbose Mode')}")
    print(f"  {dim(Icons.ARROW)}  {dim('Dir:')} {c(working_dir, Colors.CYAN)}")
    print(f"  {dim(Icons.ARROW)}  {dim('Auto-refresh:')} {c(str(auto_update), Colors.GREEN if auto_update else Colors.RED)}")


def show_verbose_step(step: int):
    print()
    print(f"  {c(Icons.PLAY, Colors.CYAN)}  {bold(f'Step {step}')}  {dim('processing…')}")


def show_verbose_function(func_name: str, func_args: dict):
    args_display = str(func_args)
    if len(args_display) > 60:
        args_display = args_display[:60] + "..."
    print(f"  {dim(Icons.ARROW)}  {c(func_name, Colors.MAGENTA)}({dim(args_display)})")


def show_verbose_result(result: str, is_error: bool = False):
    icon = Icons.ERROR if is_error else Icons.SUCCESS
    clr = Colors.RED if is_error else Colors.GREEN
    truncated = result[:VERBOSE_TRUNCATE_LENGTH] + ("..." if len(result) > VERBOSE_TRUNCATE_LENGTH else "")
    lines = truncated.split("\n")
    if len(lines) > VERBOSE_MAX_LINES:
        truncated = "\n".join(lines[:VERBOSE_MAX_LINES]) + "\n..."
    print(f"  {dim(Icons.ARROW)}  {c(icon, clr)}  {dim(truncated.replace(chr(10), ' '))}")


def show_verbose_tokens(prompt: int, response: int):
    total = prompt + response
    print(f"     {c(Icons.TOKENS, Colors.DIM)}  {dim(f'tokens: {prompt:,} in │ {response:,} out │ {total:,} total')}")


def show_function_call(func_name: str, target: str):
    """Display a tool call in non-verbose mode."""
    icon_map = {
        "get_files_info": Icons.FOLDER,
        "get_file_content": Icons.FILE,
        "get_file_outline": Icons.FILE,
        "write_file": Icons.WRITE,
        "edit_file": Icons.EDIT,
        "delete_file": Icons.DELETE,
        "run_code": Icons.PLAY,
        "run_command": Icons.GEAR,
        "search_files": Icons.SEARCH,
    }
    icon = icon_map.get(func_name, Icons.CODE)
    print(f"  {dim(icon)}  {c(Icons.ARROW, Colors.CYAN)}  {func_name}  {dim(f'({target})')}")


# ── Tool action display (Claude Code style compact lines) ───────────────

def _friendly_command_label(cmd: str) -> str:
    """Turn a shell command into a readable label."""
    cmd_lower = cmd.strip().lower()

    if cmd_lower.startswith(("pip install", "pip3 install")):
        pkg = cmd.strip().split("install", 1)[1].strip().split()[0] if "install" in cmd else "packages"
        return f"Installing {pkg}"
    if cmd_lower.startswith(("npm install", "npm i ")):
        return "Installing npm packages"
    if cmd_lower.startswith("npm init"):
        return "Initialising npm project"
    if cmd_lower.startswith("git clone"):
        return "Cloning repository"
    if cmd_lower.startswith("git init"):
        return "Initialising git repo"
    if cmd_lower.startswith("git "):
        sub = cmd.strip().split()[1] if len(cmd.strip().split()) > 1 else "op"
        return f"Git {sub}"
    if cmd_lower.startswith("npm run"):
        script = cmd.strip().split("run", 1)[1].strip().split()[0] if "run" in cmd else "script"
        return f"Running {script}"
    if cmd_lower.startswith(("mkdir", "md ")):
        return "Creating directory"
    if "pip" in cmd_lower and "upgrade" in cmd_lower:
        return "Upgrading pip"

    cmd_short = cmd.strip()[:40] + "..." if len(cmd.strip()) > 40 else cmd.strip()
    return f"Running `{cmd_short}`"


def show_action(func_name: str, func_args: dict, result=None):
    """Show a single-line, Claude Code-style action indicator."""
    global _shown_actions
    file_path = func_args.get("file_path") or func_args.get("path") or ""
    is_error = result is not None and ("Error" in str(result) or "ERROR" in str(result))

    # Dedup
    action_key = f"{func_name}:{file_path or func_args.get('command', '') or func_args.get('pattern', '')}"
    if action_key in _shown_actions:
        return
    _shown_actions.append(action_key)

    icon = Icons.ERROR if is_error else Icons.SUCCESS
    icon_color = Colors.RED if is_error else Colors.GREEN

    if func_name == "get_files_info":
        label = "Scanned workspace"
        if not is_error and isinstance(result, list):
            label += dim(f" — {len(result)} files")
    elif func_name == "get_file_content":
        label = f"Read {c(file_path, Colors.CYAN)}"
    elif func_name == "get_file_outline":
        label = f"Outlined {c(file_path, Colors.CYAN)}"
    elif func_name == "write_file":
        label = f"Created {c(file_path, Colors.CYAN)}"
    elif func_name == "edit_file":
        label = f"Edited {c(file_path, Colors.CYAN)}"
    elif func_name == "delete_file":
        label = f"Deleted {c(file_path, Colors.RED)}"
    elif func_name == "run_code":
        label = f"Ran {c(file_path or func_args.get('path', ''), Colors.CYAN)}"
    elif func_name == "search_files":
        pattern = func_args.get("pattern", "")
        label = f"Searched for {c(pattern, Colors.CYAN)}"
    elif func_name == "run_command":
        cmd = func_args.get("command", "")
        label = _friendly_command_label(cmd)
    else:
        label = func_name

    print(f"  {c(icon, icon_color)}  {label}")


# ── Error / Warning ─────────────────────────────────────────────────────

def show_error(message: str):
    """Display an error message with Claude Code-style StatusIcon."""
    print(f"  {c(Icons.ERROR, Colors.RED)}  {message}")


def show_warning(message: str):
    """Display a warning message."""
    print(f"  {c(Icons.WARNING, Colors.YELLOW)}  {bold('Warning')}: {message}")


def show_auto_fix(attempt: int, max_attempts: int = 3):
    """Auto-fix indicator."""
    print(f"  {c(Icons.FIX, Colors.YELLOW)}  {dim(f'Auto-fixing ({attempt}/{max_attempts})…')}")


# ── Agent response ──────────────────────────────────────────────────────

def show_agent_response(response_text: str):
    """Display the agent's response — clean and minimal."""
    cleaned = _strip_markdown(response_text)
    print()
    for line in cleaned.split("\n"):
        print(f"  {line}")
    print()


# ── Help ────────────────────────────────────────────────────────────────

def show_help():
    """Display available commands."""
    width = min(terminal_width(), 72)
    print()
    print(f"  {c('Commands', Colors.BOLD)}  {dim(Icons.DIVIDER * (width - 14))}")
    cmds =    [
        ("help", "Show this help"),
        ("exit / quit", "Exit"),
    ]
    for cmd, desc in cmds:
        print(f"  {c(cmd, Colors.YELLOW):<30s}  {dim(desc)}")
    print()


# ── User name prompt ────────────────────────────────────────────────────

def get_user_name() -> str:
    """Prompt for user name at startup."""
    clear_screen()
    print()
    print(f"  {c(AGENT_NAME, Colors.CYAN)}  {bold(f'v{VERSION}')}")
    print(f"  {dim(Icons.DIVIDER * 48)}")
    print(f"  {dim('Project-aware AI coding assistant')}")
    print()
    try:
        user_name = input(f"  {Icons.PROMPT}  Your name {c('>', Colors.CYAN)} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return DEFAULT_USER_NAME
    return user_name or DEFAULT_USER_NAME
