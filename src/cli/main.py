#!/usr/bin/env python3
"""CLI entry point for CodeCrafter.

This module handles only terminal-specific concerns:
- CLI argument parsing
- Input loop (read user text → call agent → display results)
- Display formatting

The actual agent logic lives in src.core.agent.AgentLoop.
"""

from __future__ import annotations

import sys

# Fix Windows Unicode
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    kernel32.SetConsoleCP(65001)
    kernel32.SetConsoleOutputCP(65001)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from src.core.settings import settings
from src.core.api_manager import OllamaClient
from src.core.agent import AgentLoop
from src.cli.display import (
    c, Colors, Icons, dim,
    show_intro_banner,
    show_exit_banner,
    show_verbose_config,
    show_help,
    show_error,
    show_warning,
    show_action,
    show_agent_response,
    show_verbose_function,
    show_verbose_result,
    show_function_call,
    get_user_name,
    reset_action_tracker,
)



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

    # Get user name and show intro
    user_name = get_user_name()
    show_intro_banner(user_name, ollama.active_model)

    if verbose_mode:
        tree_char = "\u2514\u2500"
        fallback_info = f" + {ollama.model_count() - 1} fallback(s)" if ollama.model_count() > 1 else ""
        print(
            f"  {dim('  ' + tree_char)}  Backend: {c('Ollama', Colors.CYAN)} (cloud){dim(fallback_info)}"
        )

    if verbose_mode:
        show_verbose_config(str(settings.workspace_dir), True)

    # Conversation history for the agent
    messages: list[dict] = []

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
            show_warning("Input stream closed.")
            show_exit_banner(user_name)
            break
        except KeyboardInterrupt:
            print()
            show_warning("Interrupted.")
            show_exit_banner(user_name)
            break

        if not user_prompt.strip():
            continue

        reset_action_tracker()

        cmd_lower = user_prompt.strip().lower()

        # Built-in commands
        if cmd_lower in ["e", "q", "exit", "quit"]:
            show_exit_banner(user_name)
            break

        if cmd_lower == "help":
            show_help()
            continue

        # Add user message and run agent
        messages.append({"role": "user", "content": user_prompt})
        ollama.reset()
        agent.active_model = ollama.active_model

        for step_response in agent.run_turn_streaming(
            messages,
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
                prompt_tok = usage["prompt_tokens"]
                completion_tok = usage["completion_tokens"]
                total = usage["total_tokens"]
                print(
                    f"  {dim(Icons.TOKENS)}  {dim(f'{prompt_tok:,} in | {completion_tok:,} out | {total:,} total')}"
                )




if __name__ == "__main__":
    main()
