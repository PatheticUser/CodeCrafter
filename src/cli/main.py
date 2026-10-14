"""CLI entry point for CodeCrafter acting as an adapter over canonical CodingAgent."""

from __future__ import annotations

import asyncio
import os
import sys

# Windows UTF-8 fix
if sys.platform == "win32":
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    kernel32.SetConsoleCP(65001)
    kernel32.SetConsoleOutputCP(65001)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from src.cli.display import (
    Colors,
    Icons,
    c,
    get_user_name,
    reset_action_tracker,
    show_action,
    show_agent_response,
    show_diff,
    show_exit_banner,
    show_function_call,
    show_help,
    show_intro_banner,
    show_verbose_config,
    show_warning,
    spinner,
)
from src.core.agent import CodingAgent
from src.core.events import EventType
from src.core.settings import settings
from src.llm.openai_provider import OpenAICompatibleProvider
from src.workspace.local import LocalWorkspace


def parse_args():
    """Parse command line flags."""
    args = sys.argv[1:]
    verbose = "--verbose" in args

    selected_model = settings.LLM_MODEL
    working_dir = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--model" and i + 1 < len(args):
            selected_model = args[i + 1]
            i += 2
        elif arg == "--path" and i + 1 < len(args):
            working_dir = os.path.abspath(args[i + 1])
            i += 2
        else:
            i += 1

    return verbose, selected_model, working_dir


async def run_cli_loop():
    """Async interactive CLI session."""
    verbose_mode, selected_model, custom_path = parse_args()

    workspace_path = custom_path or str(settings.workspace_root_dir)
    workspace = LocalWorkspace(workspace_id="cli-workspace", root_dir=workspace_path)

    provider = OpenAICompatibleProvider(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        model=selected_model,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        max_retries=settings.LLM_MAX_RETRIES,
        default_temperature=settings.LLM_TEMPERATURE,
    )

    agent = CodingAgent(provider=provider)
    user_name = get_user_name()
    show_intro_banner(user_name, selected_model)

    if verbose_mode:
        show_verbose_config(str(workspace.root_dir), True)

    session_id = "cli-session"
    conversation_history: list[dict] = []

    while True:
        try:
            arrow_char = "\u203a"
            prompt_str = (
                f"\n  {c(Icons.PROMPT, Colors.MAGENTA)} {c(user_name, Colors.BOLD)}"
                f" {c(arrow_char, Colors.CYAN)} "
            )
            user_prompt = input(prompt_str)
        except (EOFError, KeyboardInterrupt):
            print()
            show_exit_banner(user_name)
            break

        if not user_prompt.strip():
            continue

        cmd = user_prompt.strip().lower()
        if cmd in ("exit", "quit", "q", "e"):
            show_exit_banner(user_name)
            break
        if cmd == "help":
            show_help()
            continue

        reset_action_tracker()
        run_id = f"cli_run_{len(conversation_history)}"

        if not verbose_mode:
            spinner.start()

        try:
            async for event in agent.run(
                prompt=user_prompt,
                workspace=workspace,
                session_id=session_id,
                run_id=run_id,
                conversation_history=conversation_history,
            ):
                if not verbose_mode and spinner.is_running:
                    spinner.stop()

                if event.type == EventType.TOOL_STARTED:
                    tool_name = event.data.get("tool", "")
                    args = event.data.get("arguments", {})
                    path = args.get("file_path") or args.get("path") or args.get("command", "")
                    if verbose_mode:
                        show_function_call(tool_name, path)

                elif event.type == EventType.TOOL_COMPLETED:
                    tool_name = event.data.get("tool", "")
                    result = event.data.get("result", "")
                    diff = event.data.get("diff")
                    if not verbose_mode:
                        show_action(tool_name, {}, result)
                        if diff:
                            show_diff(diff)

                elif event.type == EventType.TOOL_FAILED:
                    tool_name = event.data.get("tool", "")
                    err = event.data.get("error", "")
                    show_warning(f"Tool {tool_name} error: {err}")

                elif event.type == EventType.AGENT_MESSAGE:
                    show_agent_response(event.data.get("content", ""))

                elif event.type == EventType.AGENT_FAILED:
                    show_warning(f"Agent failed: {event.data.get('error')}")

            # Keep conversation history bounded
            conversation_history.append({"role": "user", "content": user_prompt})

        finally:
            if spinner.is_running:
                spinner.stop()


def main():
    """Main CLI runner."""
    asyncio.run(run_cli_loop())


if __name__ == "__main__":
    main()
