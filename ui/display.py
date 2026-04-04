"""Display and UI functions for CodeCrafter, powered by Rich."""

import os
import re

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.rule import Rule

from config import (
    VERSION,
    AGENT_NAME,
    BANNER_WIDTH,
    VERBOSE_TRUNCATE_LENGTH,
    VERBOSE_MAX_LINES,
    DEFAULT_USER_NAME,
)

# Custom color theme to match Claude Code aesthetic
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "prompt": "magenta",
    "dim": "dim white",
    "highlight": "bold cyan",
})

console = Console(theme=custom_theme)

# Re-export for convenience
BANNER_WIDTH = BANNER_WIDTH


class Icons:
    AGENT = "✧"
    CODE = "⟨/⟩"
    FILE = "📄"
    FOLDER = "📁"
    SUCCESS = "✔"
    ERROR = "✖"
    WARNING = "⚠"
    INFO = "ℹ"
    PROMPT = "❯"
    ARROW = "→"
    GEAR = "⚙"
    PLAY = "▶"
    STOP = "■"
    TOKENS = "⚡"
    ACTION_OK = "✓"
    ACTION_ERR = "✗"
    BRAIN = "🧠"
    TIME = "⏱"
    SEARCH = "🔍"
    WRITE = "✍"
    DELETE = "🗑"
    DEBUG = "🐛"
    EDIT = "✏"
    FIX = "🔧"


# Legacy color classes for backward compatibility with other files
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
    """Apply legacy inline color."""
    return f"{color}{text}{Colors.RESET}"


def dim(text: str) -> str:
    """Apply legacy inline dim."""
    return f"{Colors.DIM}{text}{Colors.RESET}"


def clear_screen():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


# Track displayed actions to suppress duplicates (set for O(1) lookup)
_shown_actions: set[str] = set()


def reset_action_tracker():
    """Reset the action deduplication tracker."""
    global _shown_actions
    _shown_actions = set()


def _friendly_command_label(cmd: str, is_error: bool) -> str:
    """Turn a raw shell command into a human-readable intent label."""
    cmd_lower = cmd.strip().lower()

    if cmd_lower.startswith(("pip install", "pip3 install")):
        pkg = cmd.strip().split("install", 1)[1].strip().split()[0] if "install" in cmd else "packages"
        status = "[error]failed[/]" if is_error else "[success]done[/]"
        return f"Installing [highlight]{pkg}[/]... {status}"
    if cmd_lower.startswith(("npm install", "npm i ")):
        status = "[error]failed[/]" if is_error else "[success]done[/]"
        return f"Installing npm packages... {status}"
    if cmd_lower.startswith("npm init"):
        status = "[error]failed[/]" if is_error else "[success]done[/]"
        return f"Initializing npm project... {status}"

    if cmd_lower.startswith("git clone"):
        status = "[error]failed[/]" if is_error else "[success]done[/]"
        return f"Cloning repository... {status}"
    if cmd_lower.startswith("git "):
        sub = cmd.strip().split()[1] if len(cmd.strip().split()) > 1 else "operation"
        status = "[error]failed[/]" if is_error else "[success]done[/]"
        return f"Git {sub}... {status}"

    if cmd_lower.startswith("npm run"):
        script = cmd.strip().split("run", 1)[1].strip().split()[0] if "run" in cmd else "script"
        status = "[error]failed[/]" if is_error else "[success]done[/]"
        return f"Running [highlight]{script}[/]... {status}"

    cmd_short = cmd.strip()[:35] + "..." if len(cmd.strip()) > 35 else cmd.strip()
    status = "[error]failed[/]" if is_error else "[success]done[/]"
    return f"Running [highlight]{cmd_short}[/]... {status}"


# =============================================================================
# Banner Functions
# =============================================================================

def show_intro_banner(user_name: str, session_name: str = "", model_name: str = ""):
    """Display the intro banner."""
    clear_screen()
    console.print()
    header = Text()
    header.append(f" {Icons.AGENT}  ", style="cyan")
    header.append(f"{AGENT_NAME} ", style="bold")
    header.append(f"v{VERSION}", style="dim")
    
    console.print(header)
    console.print(Rule(style="dim", characters="─"))
    
    info = Text()
    info.append("  ")
    info.append(Icons.GEAR, style="dim")
    info.append(" Model: ")
    info.append(model_name, style="cyan")
    info.append(" │ Mode: ", style="dim")
    info.append("Interactive", style="green")
    console.print(info)
    
    if session_name:
        console.print(f"  [dim]{Icons.BRAIN}  Session:[/] [cyan]{session_name}[/]")
        
    console.print(f"  [dim]{Icons.INFO}  Type [yellow]help[/] for commands, [yellow]exit[/] to close[/]")
    console.print()
    console.print(f"  [success]{Icons.SUCCESS}[/]  Hello [magenta]{user_name}[/], ready to build something solid")
    console.print()


def show_exit_banner(user_name: str):
    """Display the exit banner."""
    console.print()
    console.print(Rule(style="dim", characters="─"))
    console.print(f"  [error]{Icons.STOP}[/]  [bold]Session Ended[/]")
    console.print(f"  [dim]{Icons.INFO}  See you soon, [magenta]{user_name}[/] <3[/]")
    console.print(Rule(style="dim", characters="─"))
    console.print()


# =============================================================================
# Action Display
# =============================================================================

def show_action(func_name: str, func_args: dict, result=None):
    """Show a single-line, human-readable description of what the agent did."""
    global _shown_actions
    file_path = func_args.get("file_path") or func_args.get("path") or ""
    try:
        is_error = result is not None and ("Error" in str(result) or "ERROR" in str(result))
    except (TypeError, ValueError):
        is_error = False

    action_key = f"{func_name}:{file_path or func_args.get('command', '') or func_args.get('pattern', '')}"
    if action_key in _shown_actions:
        return
    _shown_actions.add(action_key)

    if func_name == "get_files_info":
        label = "Scanning workspace"
        if not is_error and isinstance(result, list):
            label += f" [dim]— {len(result)} files[/]"
    elif func_name == "get_file_content":
        label = f"Reading [cyan]{file_path}[/]"
    elif func_name == "get_file_outline":
        label = f"Outlining [cyan]{file_path}[/]"
    elif func_name == "write_file":
        label = f"Created [cyan]{file_path}[/]"
    elif func_name == "edit_file":
        label = f"Edited [cyan]{file_path}[/]"
    elif func_name == "delete_file":
        label = f"Deleted [red]{file_path}[/]"
    elif func_name == "run_code":
        label = f"Executing [cyan]{file_path}[/]"
    elif func_name == "search_files":
        pattern = func_args.get("pattern", "")
        label = f"Searching for [cyan]{pattern}[/]"
    elif func_name == "run_command":
        cmd = func_args.get("command", "")
        label = _friendly_command_label(cmd, is_error)
        console.print(f"  [dim]{Icons.GEAR}[/]  {label}")
        return
    else:
        label = f"{func_name}"

    icon = f"[success]{Icons.ACTION_OK}[/]" if not is_error else f"[error]{Icons.ACTION_ERR}[/]"
    console.print(f"  {icon}  {label}")


# =============================================================================
# Verbose Mode Functions
# =============================================================================

def show_verbose_config(working_dir: str, auto_update: bool):
    console.print()
    console.print(f"  [yellow]{Icons.DEBUG}[/]  [bold]Verbose Mode[/]")
    console.print(f"  [dim]  ├─[/]  Working Dir: [cyan]{working_dir}[/]")
    console.print(f"  [dim]  └─[/]  Auto-update: [{'green' if auto_update else 'red'}]{auto_update}[/]")

def show_verbose_step(step: int):
    console.print()
    console.print(f"  [cyan]{Icons.PLAY}[/]  [bold]Step {step}[/]  [dim]processing...[/]")

def show_verbose_function(func_name: str, func_args: dict):
    args_display = str(func_args)
    if len(args_display) > 60:
        args_display = args_display[:60] + "..."
    console.print(f"  [dim]  ├─[/]  {Icons.CODE}  [magenta]{func_name}[/]([dim]{args_display}[/])")

def show_verbose_result(result: str, is_error: bool = False):
    icon = f"[error]{Icons.ERROR}[/]" if is_error else f"[success]{Icons.SUCCESS}[/]"
    truncated = result[:VERBOSE_TRUNCATE_LENGTH] + "..." if len(result) > VERBOSE_TRUNCATE_LENGTH else result
    lines = truncated.split("\n")
    if len(lines) > VERBOSE_MAX_LINES:
        truncated = "\n".join(lines[:VERBOSE_MAX_LINES]) + "\n..."
    console.print(f"  [dim]  └─[/]  {icon}  [dim]{truncated.replace(chr(10), ' ')}[/]")

def show_verbose_tokens(prompt: int, response: int):
    total = prompt + response
    console.print(f"     [dim]{Icons.TOKENS}  tokens: {prompt:,} in │ {response:,} out │ {total:,} total[/]")

def show_function_call(func_name: str, target: str):
    icon_map = {
        "get_files_info": Icons.FOLDER,
        "get_file_content": Icons.FILE,
        "run_code": Icons.PLAY,
        "run_command": Icons.GEAR,
        "search_files": Icons.SEARCH,
        "write_file": Icons.WRITE,
        "edit_file": Icons.EDIT,
    }
    icon = icon_map.get(func_name, Icons.CODE)
    console.print(f"  [dim]{icon}[/]  [cyan]{Icons.ARROW}[/]  {func_name}  [dim]({target})[/]")


# =============================================================================
# Response Display (Rich Markdown Engine)
# =============================================================================

def show_agent_response(response_text: str):
    """Render the AI response beautifully using Rich Markdown inside a panel."""
    console.print()
    md = Markdown(response_text.strip(), code_theme="monokai")
    panel = Panel(
        md, 
        title=f" {Icons.AGENT} CodeCrafter ", 
        title_align="left", 
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(panel)
    console.print()

# =============================================================================
# Notification Functions
# =============================================================================

def show_warning(message: str):
    console.print()
    console.print(f"  [warning]{Icons.WARNING}[/]  [bold]Warning[/]: {message}")

def show_error(message: str):
    console.print(f"  [error]{Icons.ERROR}[/]  {message}")

def show_auto_fix(attempt: int, max_attempts: int = 3):
    console.print(f"  [yellow]{Icons.FIX}[/]  [dim]Auto-fixing (attempt {attempt}/{max_attempts})...[/]")

def show_help():
    # Legacy wrapper
    pass

def get_user_name() -> str:
    """Prompt for user name."""
    clear_screen()
    console.print()
    console.print(f"  [cyan]{Icons.AGENT}[/]  [bold]{AGENT_NAME}[/]")
    console.print(Rule(style="dim", characters="─"))
    console.print(f"  [dim]{Icons.INFO}  Project-aware AI coding assistant[/]")
    console.print()
    try:
        user_name = input(f"  {Icons.PROMPT}  Your name > ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return DEFAULT_USER_NAME
    if not user_name:
        user_name = DEFAULT_USER_NAME
    return user_name
