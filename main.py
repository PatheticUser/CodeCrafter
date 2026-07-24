#!/usr/bin/env python3
"""
CodeCrafter - AI-powered coding assistant with multi-language execution.

A modular coding agent that provides:
- Interactive AI chat powered by Ollama
- File operations (read, write, edit, delete)
- Code execution in 15+ languages
- Session management with persistent history
- Workspace-aware context

Usage:
    python main.py [--verbose] [--model MODEL_NAME] [--path WORKING_DIR]
"""

# Fix Windows Unicode encoding issues
import sys

if sys.platform == "win32":
    import ctypes

    # Enable ANSI escape codes and UTF-8 mode
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    # Set console code page to UTF-8
    kernel32.SetConsoleCP(65001)
    kernel32.SetConsoleOutputCP(65001)
    # Force UTF-8 for stdout/stderr
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import json
import os
import re

# Configuration
from config import (
    CONTEXT_TRIM_THRESHOLD,
    DEFAULT_MODEL,
    EXECUTION_ERROR_INDICATORS,
    FALLBACK_TRIGGERS,
    FILE_MUTATING_TOOLS,
    MAX_AGENT_STEPS,
    MAX_AUTO_FIX,
    MAX_TOKENS,
    MODELS,
    TIMEOUT_INDICATOR,
)

# Core modules
from core import InferenceClient, scan_workspace_tree
from functions.delete_file import delete_file, schema_delete_file
from functions.edit_file import edit_file, schema_edit_file
from functions.get_file_content import get_file_content, schema_get_file_content
from functions.get_file_outline import get_file_outline, schema_get_file_outline

# Tool functions
from functions.get_files_info import get_files_info, schema_get_files_info
from functions.run_code import run_code, schema_run_code
from functions.run_command import run_command, schema_run_command
from functions.search_files import schema_search_files, search_files
from functions.write_file import schema_write_file, write_file

# UI modules
from ui import (
    Colors,
    Icons,
    c,
    dim,
    get_user_name,
    reset_action_tracker,
    show_action,
    show_agent_response,
    show_auto_fix,
    show_diff,
    show_error,
    show_exit_banner,
    show_function_call,
    show_help,
    show_intro_banner,
    show_model_switch,
    show_token_usage,
    show_verbose_config,
    show_verbose_function,
    show_verbose_result,
    show_verbose_step,
    show_verbose_tokens,
    show_warning,
    spinner,
)

# =============================================================================
# System Prompt Builder
# =============================================================================


def build_system_prompt(working_dir: str):
    """Build a token-efficient system prompt."""
    tree = scan_workspace_tree(working_dir)
    return f"""You are CodeCrafter, a terminal-based AI coding assistant.

OUTPUT: Plain text only. No markdown (no ** * ` # --- - 1. ```).
Keep responses 1-4 sentences. Never paste code — use tools.

WORKSPACE:
{tree}

TOOLS:
- File: get_files_info | get_file_outline (structure) | get_file_content (read with line ranges) | write_file | edit_file (search+replace) | delete_file
- Execute: run_code (auto-detect language) | run_command (shell)
- Search: search_files (grep-like)

RULES:
1. Always use tools — never paste code. write_file for new files, edit_file for changes.
2. On large files, outline first → read ranges → edit.
3. Run code after creating files to verify. If it fails, fix and retry (max 3).
4. Install dependencies before running (pip install, npm install, etc.).
5. Paths are relative to working directory.
6. Multi-file projects go in subfolders; single files at root.
"""


# =============================================================================
# Error Detection
# =============================================================================


def has_execution_error(result_str):
    """Detect if a tool result contains an execution error worth auto-fixing."""
    # Timeouts are NOT fixable errors
    if TIMEOUT_INDICATOR in result_str.lower():
        return False

    for indicator in EXECUTION_ERROR_INDICATORS:
        if indicator in result_str:
            return True
    return False


def should_fallback(error_str):
    """Check if an API error should trigger model fallback."""
    error_lower = error_str.lower()
    return any(trigger in error_lower for trigger in FALLBACK_TRIGGERS)


# =============================================================================
# Tool Registry
# =============================================================================


def get_available_tools():
    """Return list of available tool schemas."""
    return [
        schema_get_files_info,
        schema_get_file_content,
        schema_get_file_outline,
        schema_write_file,
        schema_edit_file,
        schema_delete_file,
        schema_run_code,
        schema_run_command,
        schema_search_files,
    ]


def execute_tool(func_name, func_args, working_dir, verbose=False):
    """Execute a tool by name with given arguments."""
    tools = {
        "get_files_info": lambda: get_files_info(working_dir, **{**func_args, "verbose": verbose}),
        "get_file_content": lambda: get_file_content(working_dir, **func_args),
        "get_file_outline": lambda: get_file_outline(working_dir, **func_args),
        "write_file": lambda: write_file(working_dir, **func_args),
        "edit_file": lambda: edit_file(working_dir, **func_args),
        "delete_file": lambda: delete_file(working_dir, **func_args),
        "run_code": lambda: run_code(working_dir, **func_args),
        "run_command": lambda: run_command(working_dir, **func_args),
        "search_files": lambda: search_files(working_dir, **func_args),
    }

    if func_name in tools:
        try:
            return tools[func_name]()
        except Exception as e:
            return f"ERROR executing {func_name}: {e}"
    else:
        return f"Error: Unknown function {func_name}"


# =============================================================================
# CLI Argument Parsing
# =============================================================================


def parse_args():
    """Parse command line arguments."""
    args = sys.argv[1:]
    verbose = "--verbose" in args

    # Parse --model flag
    selected_model = DEFAULT_MODEL
    working_dir = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--model" and i + 1 < len(args):
            model_key = args[i + 1]
            selected_model = MODELS.get(model_key, model_key)
            i += 2
        elif arg == "--path" and i + 1 < len(args):
            working_dir = os.path.abspath(args[i + 1])
            i += 2
        else:
            i += 1

    return verbose, selected_model, working_dir


# =============================================================================
# Main Application
# =============================================================================


def main():
    """Main entry point for CodeCrafter."""
    import config as cfg

    # Parse CLI flags
    verbose_mode, selected_model, working_dir = parse_args()

    # Override WORKING_DIR if --path was given
    if working_dir:
        cfg.WORKING_DIR = working_dir

    WDIR = cfg.WORKING_DIR

    # Initialize inference client (direct Ollama connection)
    client = InferenceClient(primary_model=selected_model)

    # Show backend info in verbose mode
    if verbose_mode:
        fallback_info = (
            f" + {client.model_count() - 1} fallback(s)" if client.model_count() > 1 else ""
        )
        print(
            f"  {dim(Icons.ARROW)}  {dim('Backend:')} {c('Ollama', Colors.CYAN)} (direct){dim(fallback_info)}"
        )

    # Get user's name
    user_name = get_user_name()

    # Show intro
    show_intro_banner(user_name, client.active_model, fallback_count=client.model_count() - 1)

    # Show verbose config
    if verbose_mode:
        show_verbose_config(WDIR, True)

    # Tool schemas
    available_tools = get_available_tools()

    # Conversation history for the agent
    messages: list[dict] = []

    # =============================================================================
    # Main Agent Loop
    # =============================================================================

    while True:
        prompt_arrow = "\u25b8"
        try:
            user_prompt = input(
                f"\n  {c(user_name, Colors.MAGENTA)} {c(prompt_arrow, Colors.CYAN)} "
            )
        except EOFError:
            print()
            show_warning("Input stream closed.")
            show_exit_banner(user_name)
            break
        except KeyboardInterrupt:
            print()
            show_warning("Interrupted by user.")
            show_exit_banner(user_name)
            break

        # Input validation
        if not user_prompt.strip():
            continue

        # Reset action dedup tracker for this turn
        reset_action_tracker()

        # Built-in commands
        cmd_lower = user_prompt.strip().lower()

        if cmd_lower in ["e", "q", "exit", "quit"]:
            show_exit_banner(user_name)
            break

        if cmd_lower == "help":
            show_help()
            continue

        # Trim conversation history: keep only last N exchanges (user+assistant pairs).
        # This prevents context overflow in long sessions.
        if len(messages) > CONTEXT_TRIM_THRESHOLD * 2:
            messages = messages[-(CONTEXT_TRIM_THRESHOLD * 2):]

        # Add user message to conversation history
        messages.append({"role": "user", "content": user_prompt})

        # Agentic Loop
        system_prompt = build_system_prompt(WDIR)
        auto_fix_count = 0
        active_model = client.active_model

        # Reset to primary model at the start of each turn
        client.reset()
        active_model = client.active_model

        for step in range(MAX_AGENT_STEPS):
            if verbose_mode:
                show_verbose_step(step + 1)
            else:
                spinner.start()

            try:
                response = client.chat_completion(
                    model=active_model,
                    messages=[{"role": "system", "content": system_prompt}] + messages,
                    tools=available_tools,
                    tool_choice="auto",
                    max_tokens=MAX_TOKENS,
                )

            except Exception as e:
                spinner.stop()
                error_str = str(e)

                # Try model fallback on recoverable errors
                if should_fallback(error_str):
                    new_model = client.fallback()
                    if new_model:
                        show_model_switch(active_model, new_model)
                        active_model = new_model
                        continue

                # Connection error (Ollama not running)
                if "connection" in error_str.lower() or "refused" in error_str.lower():
                    show_error("Cannot connect to Ollama. Make sure it is running: ollama serve")
                else:
                    show_error(f"All models failed: {e}")

                messages.pop()
                break

            spinner.stop()

            choice = response.choices[0]
            assistant_message = choice.message

            # Strip thinking blocks from reasoning models
            assistant_content = assistant_message.content or ""
            if "<think>" in assistant_content:
                assistant_content = re.sub(
                    r"<think>.*?</think>", "", assistant_content, flags=re.DOTALL
                ).strip()

            # Add assistant's response to history
            msg_to_append = {
                "role": "assistant",
                "content": assistant_content,
            }
            if assistant_message.tool_calls:
                msg_to_append["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_message.tool_calls
                ]
            messages.append(msg_to_append)

            # Handle tool calls
            if assistant_message.tool_calls:
                for tc in assistant_message.tool_calls:
                    func_name = tc.function.name
                    try:
                        func_args = json.loads(tc.function.arguments) or {}
                    except (json.JSONDecodeError, TypeError):
                        func_args = {}

                    # Get path for display
                    file_path = func_args.get("file_path") or func_args.get("path")

                    # Show verbose output
                    if verbose_mode:
                        show_function_call(
                            func_name,
                            file_path
                            or func_args.get("command", "")
                            or func_args.get("pattern", "")
                            or "context",
                        )
                        show_verbose_function(func_name, func_args)

                    # Execute the tool
                    result = execute_tool(func_name, func_args, WDIR, verbose_mode)

                    # Show output
                    if not verbose_mode:
                        show_action(func_name, func_args, result)
                        # Show diff for successful edits
                        if func_name == "edit_file" and isinstance(result, dict) and "diff" in result:
                            show_diff(result["diff"])
                    else:
                        is_error = "ERROR" in str(result) or "Error" in str(result)
                        show_verbose_result(str(result), is_error)

                    # Send tool result back to model (extract string from dict result)
                    if isinstance(result, dict) and "result" in result:
                        result_str = result["result"]
                    else:
                        result_str = (
                            json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                        )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })

                    # Refresh workspace after file-mutating operations
                    if func_name in FILE_MUTATING_TOOLS:
                        scan_workspace_tree(WDIR)  # updates prompt on next turn

                    # Auto-fix on execution errors
                    if func_name in ("run_code", "run_command") and has_execution_error(result_str):
                        if auto_fix_count < MAX_AUTO_FIX:
                            auto_fix_count += 1
                            if not verbose_mode:
                                show_auto_fix(auto_fix_count, MAX_AUTO_FIX)
                            messages.append({
                                "role": "user",
                                "content": (
                                    "The code produced an error. Read the error carefully and fix it:\n"
                                    "- If it's a missing module/package error, install the dependency using run_command "
                                    "(e.g. 'pip install package_name' or 'npm install package_name').\n"
                                    "- If it's a code error, fix it using edit_file.\n"
                                    "Then run the code again."
                                ),
                            })

            # Empty response after stripping
            elif not assistant_content:
                messages.append({
                    "role": "user",
                    "content": "Please respond using one of your available tools, or give a text answer.",
                })
                continue

            # Final text output
            else:
                content = assistant_content

                # Code-block detection
                if "```" in content and step < MAX_AGENT_STEPS - 2:
                    messages.append({
                        "role": "user",
                        "content": "Do NOT paste code in your response. Use the write_file tool to create files instead. Create the files now using write_file.",
                    })
                    spinner.stop()
                    continue

                show_agent_response(content)

                # Show token usage
                if response.usage:
                    show_token_usage(response.usage.prompt_tokens, response.usage.completion_tokens)

                break

            # Check for max steps
            if step == MAX_AGENT_STEPS - 1:
                show_warning(f"CodeCrafter reached max steps ({step + 1}). Resetting...")
                messages.clear()
                break

            # Show usage in verbose mode
            if verbose_mode and response.usage:
                usage = response.usage
                show_verbose_tokens(usage.prompt_tokens, usage.completion_tokens)


if __name__ == "__main__":
    main()
