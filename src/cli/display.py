"""Display and UI functions for CodeCrafter."""

import os
import re
import shutil

from src.core.settings import settings


def terminal_width() -> int:
    """Return the current terminal width (default 80)."""
    return shutil.get_terminal_size((80, 20)).columns


def _divider(char="\u2500", width=None) -> str:
    w = width or min(terminal_width() - 4, 48)
    return dim(char * w)


class Icons:
    # Updated Nerd Font glyphs for a richer visual experience
    SUCCESS = "\uF00C"  # check mark
    ERROR = "\uF00D"    # cross mark
    WARNING = "\uF071"  # warning triangle
    INFO = "\uF05A"     # info circle
    PROMPT = "\uF054"   # right arrow prompt
    ARROW = "\uF053"    # left arrow
    BULLET = "\uF0A0"   # bullet circle
    CODE = "\uF121"     # code symbol
    WRITE = "\uF044"    # edit (pencil)
    EDIT = "\uF040"     # edit (pencil)
    DELETE = "\uF1F8"    # trash can
    SEARCH = "\uF002"   # magnifying glass
    GEAR = "\uF013"     # gear
    PLAY = "\uF04B"     # play button
    STOP = "\uF04D"     # stop button
    TOKENS = "\u26A1"    # lightning bolt
    AGENT = "\uF2BD"    # robot face
    FIX = "\uF186"      # wrench
    DIVIDER = "\u2500"
    ELLIPSIS = "\u2026"
    FILE = "\uF15B"     # file icon
    FOLDER = "\uF115"   # folder icon
    TIME = "\uF017"     # clock
    SWITCH = "\uF21E"   # toggle switch
    BRANCH_T = "\u251C"
    BRANCH_L = "\u2514"
    PIPE = "\u2502"
    DIM_BULLET = "\uF0A0"
    DIM_ELLIPSIS = "\u2026"
    RSQUO = "\U000f0142"


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
    return f"{color}{text}{Colors.RESET}"


def dim(text: str) -> str:
    return c(text, Colors.DIM)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


_shown_actions = []


def reset_action_tracker():
    global _shown_actions
    _shown_actions = []


def _friendly_command_label(cmd, is_error):
    cmd_lower = cmd.strip().lower()
    if cmd_lower.startswith(("pip install", "pip3 install")):
        pkg = cmd.strip().split("install", 1)[1].strip().split()[0] if "install" in cmd else "packages"
        status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
        return f"Installing {c(pkg, Colors.CYAN)}... {status}"
    if cmd_lower.startswith(("npm install", "npm i ")):
        status = c("failed", Colors.RED) if is_error else c("done", Colors.GREEN)
        return "Installing npm packages... " + status
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
        script = cmd.strip().split("run", 1)[1].strip().split()[0] if "run" in cmd else "script"
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


def _word_wrap(text: str, width: int) -> str:
    if not text:
        return text
    lines = []
    for para in text.split("\n"):
        if len(para) <= width:
            lines.append(para)
        else:
            words = para.split(" ")
            line = ""
            for word in words:
                if len(line) + len(word) + 1 > width:
                    lines.append(line)
                    line = word
                else:
                    line = (line + " " + word).strip()
            if line:
                lines.append(line)
    return "\n".join(lines)


# ── Banner Functions ──────────────────────────────────────────────────────

def show_intro_banner(user_name: str, model_name: str = "", fallback_count: int = 0):
    """Display the intro banner."""
    clear_screen()
    width = min(terminal_width() - 4, 52)
    print()
    print(f"  {c(Icons.AGENT, Colors.CYAN)}  {c(settings.AGENT_NAME, Colors.BOLD)}  {dim('v' + settings.APP_VERSION)}")
    print(f"  {_divider(width=width)}")
    fallback_str = dim(f" +{fallback_count} fallback") if fallback_count else ""
    print(f"  {dim(Icons.GEAR)}  Model: {c(model_name, Colors.CYAN)}{fallback_str}")
    print(f"  {dim(Icons.INFO)}  Type {c('help', Colors.YELLOW)} for commands, {c('exit', Colors.YELLOW)} to quit")
    print()
    print(f"  {c(Icons.SUCCESS, Colors.GREEN)}  Hello {c(user_name, Colors.MAGENTA)}")
    print()


def show_exit_banner(user_name: str):
    """Display the exit banner."""
    width = min(terminal_width() - 4, 48)
    print()
    print(f"  {_divider(width=width)}")
    print(f"  {c(Icons.STOP, Colors.RED)}  {c('Goodbye', Colors.BOLD)}, {c(user_name, Colors.MAGENTA)}")
    print(f"  {_divider(width=width)}")
    print()


def show_model_switch(old_model: str, new_model: str):
    """Display model fallback."""
    arrow = "\u2192"
    print(f"  {c(Icons.SWITCH, Colors.CYAN)}  {dim(old_model)} {c(arrow, Colors.YELLOW)} {c(new_model, Colors.CYAN)}")


# ── Verbose Mode Functions ────────────────────────────────────────────────

def show_verbose_config(working_dir: str, auto_update: bool):
    width = min(terminal_width() - 4, 52)
    print()
    print(f"  {c(Icons.GEAR, Colors.YELLOW)}  {c('Verbose Mode', Colors.BOLD)}")
    print(f"  {_divider(width=width)}")
    print(f"  {dim(Icons.BRANCH_T)}  Dir: {c(working_dir, Colors.CYAN)}")
    print(f"  {dim(Icons.BRANCH_L)}  Auto-refresh: {c(str(auto_update), Colors.GREEN if auto_update else Colors.RED)}")


def show_verbose_step(step: int):
    print()
    print(f"  {c(Icons.PLAY, Colors.CYAN)}  {c(f'Step {step}', Colors.BOLD)}  {dim('processing...')}")


def show_verbose_function(func_name: str, func_args: dict):
    args_display = str(func_args)
    if len(args_display) > 60:
        args_display = args_display[:60] + "..."
    print(f"  {dim(Icons.BRANCH_T)}  {c(func_name, Colors.MAGENTA)}({dim(args_display)})")


def show_verbose_result(result: str, is_error: bool = False):
    icon = Icons.ERROR if is_error else Icons.SUCCESS
    color = Colors.RED if is_error else Colors.GREEN
    truncated = result[:settings.VERBOSE_TRUNCATE_LENGTH] + "..." if len(result) > settings.VERBOSE_TRUNCATE_LENGTH else result
    lines = truncated.split("\n")
    if len(lines) > settings.VERBOSE_MAX_LINES:
        truncated = "\n".join(lines[:settings.VERBOSE_MAX_LINES]) + "\n..."
    print(f"  {dim(Icons.BRANCH_L)}  {c(icon, color)}  {dim(truncated.replace(chr(10), ' '))}")


def show_verbose_tokens(prompt: int, response: int):
    total = prompt + response
    print(f"     {c(Icons.TOKENS, Colors.DIM)}  {dim(f'{prompt:,} in {Icons.PIPE} {response:,} out {Icons.PIPE} {total:,} total')}")


def show_function_call(func_name: str, target: str):
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
    print(f"  {c(icon, Colors.DIM)}  {c(Icons.ARROW, Colors.CYAN)}  {func_name}  {dim(f'({target})')}")


# ── Diff Display ──────────────────────────────────────────────────────

def show_diff(diff_text: str):
    """Display a unified diff with green for additions, red for removals."""
    if not diff_text.strip():
        return
    width = min(terminal_width() - 4, 72)
    print(f"  {dim(_divider(char='~', width=width))}")
    for line in diff_text.split("\n"):
        if line.startswith("+"):
            print(f"    {c(line, Colors.GREEN)}")
        elif line.startswith("-"):
            print(f"    {c(line, Colors.RED)}")
        else:
            print(f"    {dim(line)}")
    print(f"  {dim(_divider(char='~', width=width))}")


# ── Action Display ────────────────────────────────────────────────────────

def show_action(func_name: str, func_args: dict, result=None):
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

    icon = c(Icons.SUCCESS, Colors.GREEN) if not is_error else c(Icons.ERROR, Colors.RED)
    print(f"  {icon}  {label}")

    if is_error and result:
        err_preview = str(result)[:80].replace("\n", " ")
        print(f"  {dim(Icons.RSQUO)}  {dim(err_preview)}")


# ── Response Display ──────────────────────────────────────────────────────

def show_agent_response(response_text: str):
    """Display the agent's response."""
    cleaned = _strip_markdown(response_text)
    width = min(terminal_width() - 4, 72)
    print()
    print(f"  {c(Icons.AGENT, Colors.CYAN)}  {c(settings.AGENT_NAME, Colors.BOLD)}")
    print(f"  {_divider(width=width)}")
    wrapped = _word_wrap(cleaned, width)
    for line in wrapped.split("\n"):
        print(f"  {line}")
    print()


def show_token_usage(prompt_tokens: int, completion_tokens: int):
    total = prompt_tokens + completion_tokens
    print(f"  {dim(Icons.TOKENS)}  {dim(f'{prompt_tokens:,} in {Icons.PIPE} {completion_tokens:,} out {Icons.PIPE} {total:,} total')}")


# ── Notification Functions ────────────────────────────────────────────────

def show_warning(message: str):
    print()
    print(f"  {c(Icons.WARNING, Colors.YELLOW)}  {c('Warning', Colors.BOLD)}")
    print(f"  {message}")


def show_error(message: str):
    width = min(terminal_width() - 4, 48)
    print()
    print(f"  {c(Icons.ERROR, Colors.RED)}  {c('Error', Colors.BOLD)}")
    print(f"  {_divider(width=width)}")
    for line in message.split("\n"):
        print(f"  {c(line, Colors.RED)}")
    print()


def show_auto_fix(attempt: int, max_attempts: int = 3):
    print(f"  {c(Icons.FIX, Colors.YELLOW)}  {dim(f'{Icons.DIM_BULLET} Auto-fixing ({attempt}/{max_attempts})...')}")


def show_help():
    width = min(terminal_width() - 4, 52)
    print()
    print(f"  {c('Commands', Colors.BOLD)}  {_divider(width=width)}")
    print(f"  {c('help', Colors.YELLOW):<30s}  {dim('Show this help')}")
    print(f"  {c('exit / quit', Colors.YELLOW):<30s}  {dim('Exit')}")
    print()


def get_user_name() -> str:
    """Prompt for user name."""
    clear_screen()
    width = min(terminal_width() - 4, 48)
    print()
    print(f"  {c(Icons.AGENT, Colors.CYAN)}  {c(settings.AGENT_NAME, Colors.BOLD)}  {dim('v' + settings.APP_VERSION)}")
    print(f"  {_divider(width=width)}")
    print(f"  {dim('AI coding assistant for your terminal')}")
    print()
    try:
        user_name = input(f"  {Icons.PROMPT}  Your name {c('>', Colors.CYAN)} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return settings.DEFAULT_USER_NAME
    if not user_name:
        user_name = settings.DEFAULT_USER_NAME
    return user_name
