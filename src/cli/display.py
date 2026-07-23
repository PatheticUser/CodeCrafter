"""Display and UI functions for CodeCrafter."""

import os
import re

from src.core.settings import settings


class Icons:
    AGENT = ""
    CODE = ""
    FILE = ""
    FOLDER = ""
    SUCCESS = "\U000f0e4a"
    ERROR = "\U000f0028"
    WARNING = "\U000f0026"
    INFO = "\U000f059b"
    PROMPT = "\U000f0db9"
    ARROW = ""
    GEAR = "\U000f04d3"
    PLAY = "\U000f040a"
    STOP = ""
    TOKENS = "\u26a1"
    ACTION_OK = "\u2713"
    ACTION_ERR = "\u2717"
    BRAIN = "\U000f09dd"
    TIME = "\U000f06ad"
    SEARCH = "\U000f0349"
    WRITE = "\U000f03eb"
    DELETE = "\U000f01b4"
    DEBUG = "\U000f00e4"
    EDIT = "\U000f03ea"
    FIX = "\U000f0068"


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
    """Apply color to text."""
    return f"{color}{text}{Colors.RESET}"


def dim(text: str) -> str:
    """Apply dim color to text."""
    return c(text, Colors.DIM)


def clear_screen():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


_shown_actions = []


def reset_action_tracker():
    """Reset the action deduplication tracker."""
    global _shown_actions
    _shown_actions = []


def _friendly_command_label(cmd, is_error):
    """Turn a raw shell command into a human-readable intent label."""
    cmd_lower = cmd.strip().lower()

    if cmd_lower.startswith(("pip install", "pip3 install")):
        pkg = (
            cmd.strip().split("install", 1)[1].strip().split()[0]
            if "install" in cmd
            else "packages"
        )
        status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
        return f"Installing {c(pkg, Colors.CYAN)}... {status}"
    if cmd_lower.startswith(("npm install", "npm i ")):
        status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
        return f"Installing npm packages... {status}"
    if cmd_lower.startswith("npm init"):
        status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
        return f"Initializing npm project... {status}"
    if cmd_lower.startswith("git clone"):
        status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
        return f"Cloning repository... {status}"
    if cmd_lower.startswith("git init"):
        status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
        return f"Initializing git repo... {status}"
    if cmd_lower.startswith("git "):
        sub = cmd.strip().split()[1] if len(cmd.strip().split()) > 1 else "operation"
        status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
        return f"Git {sub}... {status}"
    if cmd_lower.startswith("npm run"):
        script = (
            cmd.strip().split("run", 1)[1].strip().split()[0]
            if "run" in cmd
            else "script"
        )
        status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
        return f"Running {c(script, Colors.CYAN)}... {status}"
    if cmd_lower.startswith(("mkdir", "md ")):
        status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
        return f"Creating directory... {status}"
    if "pip" in cmd_lower and "upgrade" in cmd_lower:
        status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
        return f"Upgrading pip... {status}"
    if "ensurepip" in cmd_lower:
        status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
        return f"Setting up pip... {status}"

    cmd_short = cmd.strip()[:35] + "..." if len(cmd.strip()) > 35 else cmd.strip()
    status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
    return f"Running {c(cmd_short, Colors.CYAN)}... {status}"


def _strip_markdown(text: str) -> str:
    """Remove common markdown formatting that doesn't render in terminals."""
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


# ── Banner Functions ──────────────────────────────────────────────────────


def show_intro_banner(user_name: str, model_name: str = ""):
    """Display the intro banner."""
    clear_screen()
    print()
    print(
        f"  {c(Icons.AGENT, Colors.CYAN)}  {c(settings.AGENT_NAME, Colors.BOLD)}  {dim('v' + settings.APP_VERSION)}"
    )
    divider = '\u2500' * settings.BANNER_WIDTH
    sep = '\u2502'
    print(f"  {dim(divider)}")
    print(
        f"  {dim(Icons.GEAR)}  Model: {c(model_name, Colors.CYAN)}  {dim(sep)}  Mode: {c('Interactive', Colors.GREEN)}"
    )
    print(
        f"  {dim(Icons.INFO)}  Type {c('help', Colors.YELLOW)} for commands, {c('exit', Colors.YELLOW)} to close"
    )
    print()
    print(
        f"  {c(Icons.SUCCESS, Colors.GREEN)}  Hello {c(user_name, Colors.MAGENTA)}, ready to build something solid"
    )
    print()


def show_exit_banner(user_name: str):
    """Display the exit banner."""
    print()
    line = dim('\u2500' * settings.BANNER_WIDTH)
    print(f"  {line}")
    print(f"  {c(Icons.STOP, Colors.RED)}  {c('Session Ended', Colors.BOLD)}")
    print(
        f"  {dim(Icons.INFO)}  See you soon, {c(user_name, Colors.MAGENTA)} {c('<3', Colors.MAGENTA)}"
    )
    print(f"  {line}")
    print()


# ── Verbose Mode Functions ────────────────────────────────────────────────


def show_verbose_config(working_dir: str, auto_update: bool):
    """Display verbose configuration."""
    print()
    print(f"  {c(Icons.DEBUG, Colors.YELLOW)}  {c('Verbose Mode', Colors.BOLD)}")
    branch1 = dim('  \u251c\u2500')
    branch2 = dim('  \u2514\u2500')
    print(f"  {branch1}  Working Dir: {c(working_dir, Colors.CYAN)}")
    print(
        f"  {branch2}  Auto-update: {c(str(auto_update), Colors.GREEN if auto_update else Colors.RED)}"
    )


def show_verbose_step(step: int):
    """Display verbose step indicator."""
    print()
    print(
        f"  {c(Icons.PLAY, Colors.CYAN)}  {c(f'Step {step}', Colors.BOLD)}  {dim('processing...')}"
    )


def show_verbose_function(func_name: str, func_args: dict):
    """Display verbose function call."""
    args_display = str(func_args)
    if len(args_display) > 60:
        args_display = args_display[:60] + "..."
    branch = dim('  \u251c\u2500')
    print(
        f"  {branch}  {Icons.CODE}  {c(func_name, Colors.MAGENTA)}({dim(args_display)})"
    )


def show_verbose_result(result: str, is_error: bool = False):
    """Display verbose function result."""
    icon = Icons.ERROR if is_error else Icons.SUCCESS
    color = Colors.RED if is_error else Colors.GREEN

    truncated = result[:settings.VERBOSE_TRUNCATE_LENGTH] + "..." if len(result) > settings.VERBOSE_TRUNCATE_LENGTH else result
    lines = truncated.split("\n")
    if len(lines) > settings.VERBOSE_MAX_LINES:
        truncated = "\n".join(lines[:settings.VERBOSE_MAX_LINES]) + "\n..."

    branch = dim('  \u2514\u2500')
    cleaned_res = dim(truncated.replace('\n', ' '))
    print(f"  {branch}  {c(icon, color)}  {cleaned_res}")


def show_verbose_tokens(prompt: int, response: int):
    """Display verbose token usage."""
    total = prompt + response
    token_str = f"tokens: {prompt:,} in \u2502 {response:,} out \u2502 {total:,} total"
    print(
        f"     {c(Icons.TOKENS, Colors.DIM)}  {dim(token_str)}"
    )


def show_function_call(func_name: str, target: str):
    """Display function call indicator."""
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
    print(
        f"  {c(icon, Colors.DIM)}  {c(Icons.ARROW, Colors.CYAN)}  {func_name}  {dim(f'({target})')}"
    )


# ── Action Display ────────────────────────────────────────────────────────


def show_action(func_name: str, func_args: dict, result=None):
    """Show a single-line, human-readable description of what the agent did."""
    global _shown_actions
    file_path = func_args.get("file_path") or func_args.get("path") or ""
    is_error = result is not None and ("Error" in str(result) or "ERROR" in str(result))

    action_key = f"{func_name}:{file_path or func_args.get('command', '') or func_args.get('pattern', '')}"
    if action_key in _shown_actions:
        return
    _shown_actions.append(action_key)

    if func_name == "get_files_info":
        label = "Scanning workspace"
        if not is_error and isinstance(result, list):
            label += dim(" \u2014 " + str(len(result)) + " files")
    elif func_name == "get_file_content":
        label = f"Reading {c(file_path, Colors.CYAN)}"
    elif func_name == "get_file_outline":
        label = f"Outlining {c(file_path, Colors.CYAN)}"
    elif func_name == "write_file":
        label = f"Created {c(file_path, Colors.CYAN)}"
    elif func_name == "edit_file":
        label = f"Edited {c(file_path, Colors.CYAN)}"
    elif func_name == "delete_file":
        label = f"Deleted {c(file_path, Colors.RED)}"
    elif func_name == "run_code":
        label = f"Executing {c(file_path or func_args.get('path', ''), Colors.CYAN)}"
    elif func_name == "search_files":
        pattern = func_args.get("pattern", "")
        label = f"Searching for {c(pattern, Colors.CYAN)}"
    elif func_name == "run_command":
        cmd = func_args.get("command", "")
        label = _friendly_command_label(cmd, is_error)
        print(f"  {dim(Icons.GEAR)}  {label}")
        return
    else:
        label = f"{func_name}"

    icon = Icons.ACTION_OK if not is_error else Icons.ACTION_ERR
    icon_color = Colors.GREEN if not is_error else Colors.RED
    print(f"  {c(icon, icon_color)}  {label}")


# ── Response Display ──────────────────────────────────────────────────────


def show_agent_response(response_text: str):
    """Display the agent's response."""
    cleaned = _strip_markdown(response_text)
    print()
    print(f"  {c(Icons.AGENT, Colors.CYAN)}  {c(settings.AGENT_NAME, Colors.BOLD)}")
    _line = "\u2500" * settings.BANNER_WIDTH
    print(f"  {dim(_line)}")
    for line in cleaned.split("\n"):
        print(f"  {line}")
    print()


# ── Notification Functions ────────────────────────────────────────────────


def show_warning(message: str):
    """Display a warning message."""
    print()
    print(
        f"  {c(Icons.WARNING, Colors.YELLOW)}  {c('Warning', Colors.BOLD)}: {message}"
    )


def show_error(message: str):
    """Display an error message."""
    print(f"  {c(Icons.ERROR, Colors.RED)}  {message}")


def show_auto_fix(attempt: int, max_attempts: int = 3):
    """Display auto-fix notification."""
    print(
        f"  {c(Icons.FIX, Colors.YELLOW)}  {dim(f'Auto-fixing (attempt {attempt}/{max_attempts})...')}"
    )


def show_help():
    """Display available commands."""
    print()
    print(f"  {c(Icons.INFO, Colors.CYAN)}  {c('Commands', Colors.BOLD)}")
    line = dim('\u2500' * settings.BANNER_WIDTH)
    print(f"  {line}")
    cmds =    [
        ("help", "Show this help message"),
        ("exit / quit", "Exit"),
    ]
    for cmd, desc in cmds:
        print(f"  {c(cmd, Colors.YELLOW):<30s}  {dim(desc)}")
    print()


def get_user_name() -> str:
    """Prompt for user name."""
    clear_screen()
    print()
    print(f"  {c(Icons.AGENT, Colors.CYAN)}  {c(settings.AGENT_NAME, Colors.BOLD)}")
    line = dim('\u2500' * settings.BANNER_WIDTH)
    print(f"  {line}")
    print(f"  {dim(Icons.INFO)}  Project-aware AI coding assistant")
    print()
    try:
        user_name = input(f"  {Icons.PROMPT}  Your name {c('>', Colors.CYAN)} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return settings.DEFAULT_USER_NAME
    if not user_name:
        user_name = settings.DEFAULT_USER_NAME
    return user_name
