#!/usr/bin/env python3
"""CLI entry point for CodeCrafter.

This module handles only terminal-specific concerns:
- CLI argument parsing
- Input loop (read user text → call agent → display results)
- Session commands (help, sessions, exit)
- Display formatting

The actual agent logic lives in src.core.agent.AgentLoop.
"""

from __future__ import annotations

import sys
import os

# Fix Windows Unicode
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    kernel32.SetConsoleCP(65001)
    kernel32.SetConsoleOutputCP(65001)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import json
import re

from src.core.settings import settings
from src.core.api_manager import OllamaClient
from src.core.workspace import scan_workspace_tree
from src.core.agent import AgentLoop
from src.cli.display import (
    c, Colors, Icons, dim,
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
from src.sessions import SessionManager, list_sessions, delete_session_file
from src.tools.registry import ToolRegistry


def parse_args():
    """Parse command line arguments."""
    args = sys.argv[1:]
    verbose = "--verbose" in args

    selected_model = settings.DEFAULT_MODEL
    for i, arg in enumerate(args):
        if arg == "--model" and i + 1 < len(args):
            model_key = args[i + 1]
            selected_model = settings.MODELS.get(model_key, model_key)

    return verbose, selected_model


def main():
    """Main entry point for CodeCrafter CLI."""
    verbose_mode, selected_model = parse_args()

    # Initialize Ollama client
    ollama = OllamaClient(primary_model=selected_model)
    client = ollama.get_client()

    # Initialize agent loop
    agent = AgentLoop(client=client, model=ollama.active_model)

    # Initialize session manager
    session_mgr = SessionManager()

    # Get user name and show intro
    user_name = get_user_name()
    show_intro_banner(user_name, session_mgr.current_session_name, ollama.active_model)

    if verbose_mode:
        tree_char = "\u2514\u2500"
        fallback_info = f" + {ollama.model_count() - 1} fallback(s)" if ollama.model_count() > 1 else ""
        print(
            f"  {dim('  ' + tree_char)}  Backend: {c('Ollama', Colors.CYAN)} (cloud){dim(fallback_info)}"
        )

    if verbose_mode:
        show_verbose_config(str(settings.workspace_dir), True)

    if session_mgr.messages and verbose_mode:
        print(f"  {dim(Icons.INFO)}  Restored {len(session_mgr.messages)} messages from session")

    # ==========================================================================
    # Main Agent Loop
    # ==========================================================================

    while True:
        try:
            user_prompt = input(
                f"\n  {c(Icons.PROMPT, Colors.MAGENTA)} {c(user_name, Colors.BOLD)} {c('\u203a', Colors.CYAN)} "
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

        reset_action_tracker()

        cmd_lower = user_prompt.strip().lower()

        # Built-in commands
        if cmd_lower in ["e", "q", "exit", "quit"]:
            session_mgr.save()
            show_exit_banner(user_name)
            break

        if cmd_lower == "help":
            show_help()
            continue

        if cmd_lower == "sessions":
            sessions = list_sessions()
            if not sessions:
                print(f"  {dim(Icons.INFO)}  No saved sessions found.")
                continue
            print()
            print(f"  {c(Icons.BRAIN, Colors.CYAN)}  {c('Saved Sessions', Colors.BOLD)}")
            print(f"  {dim('\u2500' * 52)}")
            for i, s in enumerate(sessions):
                marker = c(Icons.ARROW, Colors.CYAN) if i == 0 else " "
                print(f"  {marker}  {c(s['name'], Colors.CYAN)}  {dim(s['modified'] + '  |  ' + str(s['messages']) + ' msgs')}")
            print()
            continue

        if cmd_lower == "session new":
            new_name = session_mgr.new_session()
            print(
                f"  {c(Icons.SUCCESS, Colors.GREEN)}  New session: {c(new_name, Colors.CYAN)}"
            )
            continue

        if cmd_lower.startswith("session load "):
            target = user_prompt.strip()[len("session load "):].strip()
            if not target:
                show_error("Usage: session load <name>")
                continue
            try:
                name, msg_count = session_mgr.load(target)
                print(
                    f"  {c(Icons.SUCCESS, Colors.GREEN)}  Loaded session: {c(name, Colors.CYAN)} ({msg_count} messages)"
                )
            except Exception as e:
                show_error(f"Failed to load session: {e}")
            continue

        if cmd_lower.startswith("session delete "):
            target = user_prompt.strip()[len("session delete "):].strip()
            if not target:
                show_error("Usage: session delete <name>")
                continue
            if target == session_mgr.current_session_name:
                show_error("Cannot delete the active session. Switch first.")
                continue
            if delete_session_file(target):
                print(
                    f"  {c(Icons.SUCCESS, Colors.GREEN)}  Deleted session: {c(target, Colors.CYAN)}"
                )
            else:
                show_error(f"Session '{target}' not found.")
            continue

        if cmd_lower == "clear":
            session_mgr.clear()
            print(f"  {dim(Icons.INFO)}  Session cleared")
            continue

        # Add user message and run agent
        session_mgr.add_message("user", user_prompt)
        ollama.reset()
        agent.active_model = ollama.active_model

        for step_response in agent.run_turn_streaming(
            session_mgr.get_messages(),
            str(settings.workspace_dir),
        ):
            if step_response.tool_calls:
                for tc, tr in zip(step_response.tool_calls, step_response.tool_results):
                    func_name = tc["name"]
                    func_args = tc["arguments"]
                    result = tr["result"]

                    file_path = func_args.get("file_path") or func_args.get("path")

                    if verbose_mode:
                        show_function_call(
                            func_name,
                            file_path or func_args.get("command", "") or func_args.get("pattern", "") or "context",
                        )
                        show_verbose_function(func_name, func_args)
                    else:
                        show_action(func_name, func_args, result)

                    if verbose_mode:
                        is_error = "ERROR" in str(result) or "Error" in str(result)
                        show_verbose_result(str(result), is_error)

                    # Refresh workspace after file-mutating operations
                    if func_name in settings.FILE_MUTATING_TOOLS:
                        pass  # workspace tree will be refreshed on next system prompt

            if step_response.text:
                show_agent_response(step_response.text)

            if step_response.token_usage:
                usage = step_response.token_usage
                total = usage["total_tokens"]
                print(
                    f"  {dim(Icons.TOKENS)}  {dim(f'{usage[\"prompt_tokens\"]:,} in | {usage[\"completion_tokens\"]:,} out | {total:,} total')}"
                )

        # Save after each turn
        session_mgr.save()


if __name__ == "__main__":
    main()
