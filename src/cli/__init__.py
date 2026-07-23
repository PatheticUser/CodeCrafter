"""CLI-specific UI code: display formatting, spinner, ANSI colors.

The CLI layer imports from core but core never imports from here.
"""

from src.cli.display import (
    Icons,
    Colors,
    c,
    dim,
    clear_screen,
    show_intro_banner,
    show_exit_banner,
    show_verbose_config,
    show_help,
    show_error,
    show_warning,
    show_action,
    show_agent_response,
    show_auto_fix,
    show_verbose_step,
    show_verbose_function,
    show_verbose_result,
    show_verbose_tokens,
    show_function_call,
    get_user_name,
    reset_action_tracker,
)
from src.cli.spinner import Spinner, spinner

__all__ = [
    "Icons",
    "Colors",
    "c",
    "dim",
    "clear_screen",
    "show_intro_banner",
    "show_exit_banner",
    "show_verbose_config",
    "show_help",
    "show_error",
    "show_warning",
    "show_action",
    "show_agent_response",
    "show_auto_fix",
    "show_verbose_step",
    "show_verbose_function",
    "show_verbose_result",
    "show_verbose_tokens",
    "show_function_call",
    "get_user_name",
    "Spinner",
    "spinner",
    "reset_action_tracker",
]
