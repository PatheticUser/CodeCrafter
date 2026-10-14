"""Display and UI functions for CodeCrafter — rich-powered, full-width TUI.

Layout follows modern agentic CLIs (Claude Code et al.):
- every element spans the full terminal width (2-column margins)
- tool calls render as a single ``⏺ Verb(target)`` line with a collapsed ``⎿`` detail
- assistant replies render under a hanging ``⏺`` bullet (markdown when present)
"""

import io
import os
import re
import shutil

from rich.cells import cell_len
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text

from config import (
    AGENT_NAME,
    DEFAULT_USER_NAME,
    VERBOSE_TRUNCATE_LENGTH,
    VERSION,
)

# ── Console ─────────────────────────────────────────────────────────────────

console = Console(highlight=False, emoji=False)

# Leading margin applied to every line so content keeps a 2-column gutter.
MARGIN = "  "


# ── Terminal width ──────────────────────────────────────────────────────────


def terminal_width() -> int:
    """Return the current terminal width (default 80)."""
    return shutil.get_terminal_size((80, 20)).columns


def content_width() -> int:
    """Full-width content area: terminal minus a 2-column margin on each side."""
    return max(30, terminal_width() - 4)


# ── Colour / style helpers (ANSI, for callers that print directly) ──────────


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


# ── Icons (portable Unicode — no Nerd Font required) ────────────────────────


class Icons:
    SUCCESS = "\u2713"  # check mark
    ERROR = "\u2717"  # cross mark
    WARNING = "\u26a0"  # warning sign
    INFO = "\u2139"  # info
    PROMPT = "\u276f"  # heavy right-pointing angle quotation mark
    ARROW = "\u2192"  # rightwards arrow
    BULLET = "\u2022"  # bullet
    CODE = "</>"
    WRITE = "\u270e"  # pencil
    EDIT = "\u270e"  # pencil
    DELETE = "\u232b"  # erase to the left
    SEARCH = "\U0001f50d"  # magnifying glass
    GEAR = "\u2699"  # gear
    PLAY = "\u25b6"  # play
    STOP = "\u25a0"  # black square
    TOKENS = "\u26a1"  # high voltage
    AGENT = "\u2733"  # eight spoked asterisk
    FIX = "\u21bb"  # clockwise open circle arrow
    DIVIDER = "\u2500"
    ELLIPSIS = "\u2026"
    FILE = "\U0001f4c4"  # page
    FOLDER = "\U0001f4c1"  # folder
    TIME = "\u23f1"  # stopwatch
    SWITCH = "\u21c4"  # rightwards arrow over leftwards arrow
    BRANCH_T = "\u251c"
    BRANCH_L = "\u2514"
    PIPE = "\u2502"
    DIM_BULLET = "\u2022"
    DIM_ELLIPSIS = "\u2026"


# ── Action deduplication ────────────────────────────────────────────────────

_shown_actions: list[str] = []


def reset_action_tracker():
    global _shown_actions
    _shown_actions = []


# ── Text helpers ────────────────────────────────────────────────────────────


def _word_wrap(text: str, width: int) -> str:
    """Word-wrap text to fit the given width."""
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


def _truncate(text: str, width: int) -> str:
    """Collapse whitespace and truncate to width with an ellipsis."""
    text = " ".join(str(text).split())
    if width <= 1:
        return "\u2026"
    if len(text) <= width:
        return text
    return text[: width - 1] + "\u2026"


def _first_line(result) -> str:
    """First non-empty line of a result."""
    for line in str(result).strip().split("\n"):
        if line.strip():
            return line.strip()
    return ""


def _rule() -> Text:
    """A full-width horizontal divider."""
    return Text(MARGIN + "\u2500" * content_width(), style="dim")


def _heading(title: str) -> Text:
    """A section title followed by a rule that fills the remaining width."""
    t = Text(MARGIN)
    t.append(title, style="bold")
    t.append("  ")
    remaining = content_width() - cell_len(title) - 4
    if remaining > 0:
        t.append("\u2500" * remaining, style="dim")
    return t


# ── Screen ──────────────────────────────────────────────────────────────────


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


# ── Intro banner ────────────────────────────────────────────────────────────


def show_intro_banner(user_name: str, model_name: str = "", fallback_count: int = 0):
    """Startup banner — full-width header with model on the right."""
    clear_screen()
    width = content_width()

    left = Text(MARGIN)
    left.append(f"{AGENT_NAME} ", style="bold cyan")
    left.append(f"v{VERSION}", style="dim")

    right = Text()
    if model_name:
        right.append(model_name, style="cyan")
    if fallback_count:
        right.append(f" +{fallback_count} fallbacks", style="dim")

    header = Text()
    header.append_text(left)
    gap = width - cell_len(left.plain) - cell_len(right.plain)
    header.append(" " * max(1, gap))
    header.append_text(right)

    console.print()
    console.print(header)
    console.print(_rule())
    greeting = Text(MARGIN)
    greeting.append(f"{Icons.SUCCESS} ", style="green")
    greeting.append(f"Hello {user_name}", style="bold magenta")
    greeting.append("  \u00b7  ", style="dim")
    greeting.append("type ", style="dim")
    greeting.append("help", style="yellow")
    greeting.append(" for commands, ", style="dim")
    greeting.append("exit", style="yellow")
    greeting.append(" to quit", style="dim")
    console.print(greeting)
    console.print()


# ── Exit banner ─────────────────────────────────────────────────────────────


def show_exit_banner(user_name: str):
    """Exit message."""
    console.print()
    console.print(_rule())
    t = Text(MARGIN)
    t.append(f"{Icons.STOP} ", style="red")
    t.append("Goodbye ", style="bold")
    t.append(user_name, style="bold magenta")
    t.append(".", style="bold")
    console.print(t)
    console.print(_rule())
    console.print()


# ── Model fallback display ──────────────────────────────────────────────────


def show_model_switch(old_model: str, new_model: str):
    """Display when the model switches due to fallback."""
    t = Text(MARGIN)
    t.append(f"{Icons.SWITCH} ", style="cyan")
    t.append(old_model, style="dim")
    t.append(" \u2192 ", style="yellow")
    t.append(new_model, style="cyan")
    console.print(t)


# ── Verbose mode ────────────────────────────────────────────────────────────


def show_verbose_config(working_dir: str, auto_update: bool):
    console.print()
    console.print(_heading("Verbose Mode"))
    t = Text(MARGIN)
    t.append(f"{Icons.BRANCH_T} ", style="dim")
    t.append("Dir: ", style="dim")
    t.append(working_dir, style="cyan")
    console.print(t)
    t = Text(MARGIN)
    t.append(f"{Icons.BRANCH_L} ", style="dim")
    t.append("Auto-refresh: ", style="dim")
    t.append(str(auto_update), style="green" if auto_update else "red")
    console.print(t)


def show_verbose_step(step: int):
    console.print()
    t = Text(MARGIN)
    t.append(f"{Icons.PLAY} ", style="cyan")
    t.append(f"Step {step}", style="bold")
    t.append(" processing\u2026", style="dim")
    console.print(t)


def show_function_call(func_name: str, target: str):
    """Display a tool call in verbose mode."""
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
    t = Text(MARGIN)
    t.append(f"{icon} ", style="dim")
    t.append(f"{Icons.ARROW} ", style="cyan")
    t.append(func_name, style="magenta")
    t.append(f"({_truncate(target, max(10, content_width() - 30))})", style="dim")
    console.print(t)


def show_verbose_function(func_name: str, func_args: dict):
    args_display = str(func_args)
    if len(args_display) > 60:
        args_display = args_display[:60] + "\u2026"
    t = Text(MARGIN)
    t.append(f"{Icons.BRANCH_T} ", style="dim")
    t.append(func_name, style="magenta")
    t.append(f"({args_display})", style="dim")
    console.print(t)


def show_verbose_result(result: str, is_error: bool = False):
    icon = Icons.ERROR if is_error else Icons.SUCCESS
    style = "red" if is_error else "green"
    flat = " ".join(str(result).split())
    if len(flat) > VERBOSE_TRUNCATE_LENGTH:
        flat = flat[:VERBOSE_TRUNCATE_LENGTH] + "\u2026"
    t = Text(MARGIN)
    t.append(f"{Icons.BRANCH_L} ", style="dim")
    t.append(f"{icon} ", style=style)
    t.append(_truncate(flat, content_width() - 7), style="dim")
    console.print(t)


def show_verbose_tokens(prompt: int, response: int):
    show_token_usage(prompt, response)


# ── Diff display ────────────────────────────────────────────────────────────


def show_diff(diff_text: str):
    """Display a unified diff spanning the full terminal width."""
    if not diff_text.strip():
        return
    bar = Text(MARGIN + "~" * content_width(), style="dim")
    console.print(bar)
    body_width = content_width() - 4
    for raw in diff_text.split("\n"):
        if raw.startswith("+++") or raw.startswith("---"):
            style = "dim"
        elif raw.startswith("+"):
            style = "green"
        elif raw.startswith("-"):
            style = "red"
        elif raw.startswith("@@"):
            style = "cyan"
        else:
            style = ""
        if not raw:
            console.print()
            continue
        for chunk in _word_wrap(raw, body_width).split("\n"):
            console.print(Text("    " + chunk, style=style))
    console.print(bar)


# ── Action display ──────────────────────────────────────────────────────────

# verb + accent colour per tool (Claude Code-style Verb(target) lines)
_TOOL_VERBS = {
    "get_files_info": ("Scan", "cyan"),
    "get_file_content": ("Read", "cyan"),
    "get_file_outline": ("Outline", "cyan"),
    "write_file": ("Write", "green"),
    "edit_file": ("Edit", "green"),
    "delete_file": ("Delete", "red"),
    "run_code": ("Run", "yellow"),
    "run_command": ("Bash", "yellow"),
    "search_files": ("Grep", "magenta"),
}


def _action_target(func_name: str, func_args: dict, file_path: str) -> str:
    if func_name == "run_command":
        return _truncate(str(func_args.get("command", "")), max(10, content_width() - 14))
    if func_name == "search_files":
        return f'"{func_args.get("pattern", "")}"'
    if func_name == "get_files_info":
        return str(func_args.get("path") or "workspace")
    if func_name == "run_code" and not file_path:
        return "code"
    return file_path or "context"


def _action_detail(
    func_name: str, func_args: dict, result, is_error: bool
) -> tuple[str | None, str]:
    """One-line ``⎿`` summary shown under an action (or None)."""
    width = max(10, content_width() - 4)
    if result is None:
        return None, "dim"

    s = str(result).strip()
    if not s:
        return None, "dim"

    if func_name in ("run_code", "run_command"):
        code_match = re.search(r"EXIT CODE: (\d+)", s)
        code = int(code_match.group(1)) if code_match else None
        failed = bool(is_error) or code not in (None, 0)
        stdout_lines, stderr_lines, other_lines = _split_run_output(s)
        if failed and stderr_lines:
            content = stderr_lines
        elif stdout_lines:
            content = stdout_lines
        else:
            content = other_lines
        style = "red" if failed else ("green" if code == 0 else "dim")
        pieces: list[str] = []
        if content:
            pieces.append(_truncate(content[0], max(8, width - 20)))
            if len(content) > 1:
                pieces.append(f"+{len(content) - 1} more lines")
        if code is not None:
            pieces.append(f"exit {code}")
        if not pieces:
            pieces.append(_truncate(_first_line(s), width))
        return _truncate(" \u00b7 ".join(pieces), width), style

    if is_error:
        return _truncate(_first_line(result) or "failed", width), "red"

    if isinstance(result, list):
        n = len(result)
        return f"{n} {'file' if n == 1 else 'files'}", "dim"

    if isinstance(result, dict) and "diff" in result:
        added = sum(
            1
            for ln in str(result.get("diff", "")).splitlines()
            if ln.startswith("+") and not ln.startswith("+++")
        )
        removed = sum(
            1
            for ln in str(result.get("diff", "")).splitlines()
            if ln.startswith("-") and not ln.startswith("---")
        )
        return f"+{added} \u2212{removed}", "green"

    if func_name == "get_file_content":
        m = re.search(r"\u2014 (\d+) lines", s)
        if m:
            note = " (head + tail)" if "showing head + tail" in s else ""
            return f"{m.group(1)} lines{note}", "dim"
        m = re.search(r"lines (\d+)-(\d+) of (\d+)", s)
        if m:
            return f"lines {m.group(1)}-{m.group(2)} of {m.group(3)}", "dim"
        return _truncate(_first_line(s).strip("[]"), width), "dim"

    if func_name == "get_file_outline":
        n = len([ln for ln in s.splitlines() if ln.strip()])
        return f"{n} lines of structure", "dim"

    if func_name == "write_file":
        m = re.search(r"\((\d+) characters written\)", s)
        if m:
            return f"{m.group(1)} characters", "dim"
        return _truncate(_first_line(s), width), "dim"

    if func_name == "search_files":
        if "No matches found" in s:
            return "no matches", "dim"
        n = len([ln for ln in s.splitlines() if ln.strip()])
        return f"{n} {'match' if n == 1 else 'matches'}", "dim"

    return _truncate(_first_line(s), width), "dim"


def _split_run_output(s: str) -> tuple[list[str], list[str], list[str]]:
    """Split a run result into stdout lines, stderr lines, and other lines."""
    stdout: list[str] = []
    stderr: list[str] = []
    other: list[str] = []
    target = other
    for ln in s.splitlines():
        st = ln.strip()
        if st == "STDOUT:":
            target = stdout
            continue
        if st == "STDERR:":
            target = stderr
            continue
        if st.startswith("EXIT CODE"):
            target = other
            continue
        if st:
            target.append(st)
    return stdout, stderr, other


def show_action(func_name: str, func_args: dict, result=None):
    """Show a Claude Code-style ``⏺ Verb(target)`` line with a collapsed detail."""
    global _shown_actions
    file_path = func_args.get("file_path") or func_args.get("path") or ""
    result_str = "" if result is None else str(result)
    is_error = bool(result) and (
        "Error" in result_str
        or "ERROR" in result_str
        or re.search(r"EXIT CODE: [1-9]\d*", result_str)
    )

    # Dedup
    action_key = (
        f"{func_name}:{file_path or func_args.get('command', '') or func_args.get('pattern', '')}"
    )
    if action_key in _shown_actions:
        return
    _shown_actions.append(action_key)

    verb, color = _TOOL_VERBS.get(func_name, (func_name, "cyan"))
    target = _action_target(func_name, func_args, file_path)
    detail, detail_style = _action_detail(func_name, func_args, result, bool(is_error))

    marker = "\u2717" if is_error else "\u23fa"  # ✕ on error, ⏺ otherwise
    line = Text(MARGIN)
    line.append(f"{marker} ", style="red" if is_error else color)
    line.append(verb, style=f"bold {color}")
    line.append("(", style="dim")
    line.append(target, style=color)
    line.append(")", style="dim")
    console.print(line)

    if detail:
        d = Text("    \u23bf ")  # ⎿ tree terminator
        d.append(detail, style=detail_style)
        console.print(d)


# ── Error / Warning ─────────────────────────────────────────────────────────


def show_error(message: str):
    """Display an error in a full-width bordered box (2-column margins)."""
    total = content_width()
    inner = total - 4  # text width between '\u2502 ' and ' \u2502'
    title = " Error "
    k = total - 3 - cell_len(title)

    console.print()
    console.print(
        Text(MARGIN + "\u256d\u2500" + title + "\u2500" * max(0, k) + "\u256f", style="red")
    )
    for line in message.split("\n"):
        for chunk in _word_wrap(line, inner).split("\n") or [""]:
            body = f"\u2502 {chunk.ljust(inner)} \u2502"
            console.print(Text(MARGIN + body, style="red"))
    console.print(Text(MARGIN + "\u2570" + "\u2500" * (total - 2) + "\u256f", style="red"))
    console.print()


def show_warning(message: str):
    """Display a warning message."""
    t = Text(MARGIN)
    t.append(f"{Icons.WARNING} ", style="yellow")
    t.append("Warning  ", style="bold yellow")
    t.append(message, style="yellow")
    console.print(t)


def show_auto_fix(attempt: int, max_attempts: int = 3):
    """Auto-fix indicator."""
    t = Text(MARGIN)
    t.append(f"{Icons.FIX} ", style="yellow")
    t.append(f"Auto-fixing ({attempt}/{max_attempts})", style="yellow")
    t.append("  \u00b7 asking the model to correct the error\u2026", style="dim")
    console.print(t)


# ── Agent response ──────────────────────────────────────────────────────────

_MD_RE = re.compile(r"(```|^#{1,6}[ \t]|^[ \t]*[-*][ \t]|^[ \t]*\d+\.[ \t]|\*\*|`)", re.MULTILINE)


def _markdown_lines(text: str, width: int) -> list[str]:
    """Render markdown into pre-wrapped ANSI lines at the given width."""
    buf = io.StringIO()
    capture = Console(
        file=buf,
        width=max(20, width),
        force_terminal=True,
        color_system="standard",
        highlight=False,
    )
    capture.print(Markdown(text))
    return buf.getvalue().split("\n")


def show_agent_response(response_text: str, agent_name: str = AGENT_NAME):
    """Display the agent's response under a hanging ``⏺`` bullet."""
    if not response_text or not response_text.strip():
        return
    width = content_width()
    console.print()

    if _MD_RE.search(response_text):
        lines = _markdown_lines(response_text, width - 2)
        from_ansi = True
    else:
        lines = []
        for para in response_text.split("\n"):
            if not para.strip():
                lines.append("")
            else:
                lines.extend(_word_wrap(para, width - 2).split("\n"))
        from_ansi = False

    while lines and not lines[-1].strip():
        lines.pop()

    first = True
    for line in lines:
        if not line.strip():
            console.print()
            continue
        t = Text()
        if first:
            t.append(MARGIN)
            t.append("\u23fa ", style="cyan")  # ⏺
            first = False
        else:
            t.append(" " * 4)
        t.append_text(Text.from_ansi(line) if from_ansi else Text(line))
        console.print(t)
    console.print()


# ── Token usage ─────────────────────────────────────────────────────────────


def show_token_usage(prompt_tokens: int, completion_tokens: int):
    """Show token usage in a compact, visual format."""
    total = prompt_tokens + completion_tokens
    t = Text(MARGIN)
    t.append(f"{Icons.TOKENS} ", style="dim")
    t.append(f"{prompt_tokens:,} in", style="dim")
    t.append(f" {Icons.PIPE} ", style="dim")
    t.append(f"{completion_tokens:,} out", style="dim")
    t.append(f" {Icons.PIPE} ", style="dim")
    t.append(f"{total:,} total", style="bold dim")
    console.print(t)


# ── Help ────────────────────────────────────────────────────────────────────


def _help_rows(rows: list[tuple[str, str]], gap: int = 16):
    for label, desc in rows:
        t = Text(MARGIN)
        t.append(label, style="yellow")
        t.append(" " * max(1, gap - cell_len(label)))
        t.append(desc, style="dim")
        console.print(t)


def show_help():
    """Display available commands, full width."""
    console.print()
    console.print(_heading("Commands"))
    _help_rows(
        [
            ("help", "Show this help"),
            ("exit / quit", "Exit the session (also q, e)"),
        ]
    )
    console.print()
    console.print(_heading("CLI flags"))
    _help_rows(
        [
            ("--verbose", "Step-by-step tool output"),
            ("--model X", "Override model name"),
            ("--path DIR", "Use a different workspace directory"),
        ]
    )
    console.print()


# ── Input prompt ────────────────────────────────────────────────────────────


def prompt_prefix() -> str:
    """Prompt string used before user input (raw ANSI for ``input()``)."""
    return f"\n  {Colors.BOLD}{Colors.CYAN}{Icons.PROMPT}{Colors.RESET} "


# ── User name prompt ────────────────────────────────────────────────────────


def get_user_name() -> str:
    """Prompt for user name at startup."""
    clear_screen()
    console.print()
    console.print(_heading(f"{AGENT_NAME} v{VERSION}"))
    console.print(Text(MARGIN + "AI coding assistant for your terminal", style="dim"))
    console.print()
    try:
        marker = f"{Colors.BOLD}{Colors.CYAN}{Icons.PROMPT}{Colors.RESET}"
        user_name = input(f"  {marker} Your name {c('>', Colors.CYAN)} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return DEFAULT_USER_NAME
    return user_name or DEFAULT_USER_NAME
