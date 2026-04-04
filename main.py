#!/usr/bin/env python3
"""CodeCrafter — AI-powered coding assistant with multi-language execution.

Usage:
    python main.py [--verbose] [--model MODEL_NAME]
"""

# Fix Windows Unicode encoding issues
import sys
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    kernel32.SetConsoleCP(65001)
    kernel32.SetConsoleOutputCP(65001)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import argparse

from config import VERSION, DEFAULT_MODEL, MODELS, WORKING_DIR
from services.logger import setup_logging
from core import OllamaClient, AgentLoop
from chat_session import SessionManager
from tools import ToolRegistry
from commands import create_command_registry
from ui import (
    c, Colors, Icons, dim,
    show_intro_banner,
    show_exit_banner,
    show_warning,
    show_verbose_config,
    get_user_name,
    reset_action_tracker,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="CodeCrafter — AI-powered coding assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose step-by-step output",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Primary model name or shortcut ({', '.join(MODELS.keys())})",
    )
    parser.add_argument(
        "--version", action="version", version=f"CodeCrafter v{VERSION}",
    )
    args = parser.parse_args()

    # Resolve model shortcut
    args.model = MODELS.get(args.model, args.model)
    return args


def main() -> None:
    """Main entry point for CodeCrafter."""
    args = parse_args()

    # Initialize logging
    setup_logging(verbose=args.verbose)

    # Initialize core components
    ollama = OllamaClient(primary_model=args.model)
    session_mgr = SessionManager()
    tool_registry = ToolRegistry(working_directory=WORKING_DIR)
    command_registry = create_command_registry()

    # Get user's name
    user_name = get_user_name()

    # Show intro
    show_intro_banner(user_name, session_mgr.current_session_name, ollama.active_model)

    if args.verbose:
        fallback_info = f" + {ollama.model_count() - 1} fallback(s)" if ollama.model_count() > 1 else ""
        print(f"  {dim('  └─')}  Backend: {c('Ollama', Colors.CYAN)} (cloud){dim(fallback_info)}")
        show_verbose_config(WORKING_DIR, True)
        if session_mgr.messages:
            print(f"  {dim(Icons.INFO)}  Restored {len(session_mgr.messages)} messages from session")

    # Shared context for commands
    context = {
        "session_mgr": session_mgr,
        "user_name": user_name,
        "should_exit": False,
    }

    # ==========================================================================
    # Main REPL Loop
    # ==========================================================================

    while True:
        try:
            user_prompt = input(
                f"\n  {c(Icons.PROMPT, Colors.MAGENTA)} {c(user_name, Colors.BOLD)} {c('›', Colors.CYAN)} "
            )
        except EOFError:
            print()
            session_mgr.save()
            show_warning("Input stream closed. Session saved.")
            show_exit_banner(user_name)
            break
        except KeyboardInterrupt:
            print()
            session_mgr.save()
            show_warning("Interrupted by user. Session saved.")
            show_exit_banner(user_name)
            break

        if not user_prompt.strip():
            continue

        # Reset action dedup tracker for this turn
        reset_action_tracker()

        # Try built-in commands first
        handled = command_registry.try_handle(user_prompt, context)
        if handled:
            if context.get("should_exit"):
                break
            continue

        # Add user message to session
        session_mgr.add_message("user", user_prompt)

        # Run the agentic loop
        agent = AgentLoop(
            ollama=ollama,
            session_mgr=session_mgr,
            tool_registry=tool_registry,
            verbose=args.verbose,
        )
        agent.run()


if __name__ == "__main__":
    main()
