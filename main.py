#!/usr/bin/env python3
"""
CodeCrafter - AI-powered coding assistant with multi-language execution.

A modular coding agent that provides:
- Interactive AI chat with Groq API
- File operations (read, write, edit, delete)
- Code execution in 15+ languages
- Session management with persistent history
- Workspace-aware context

Usage:
    python main.py [--verbose] [--model MODEL_NAME]
"""

# Fix Windows Unicode encoding issues
import sys
import os
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
import re

# Configuration
from config import (
    VERSION,
    MODELS,
    DEFAULT_MODEL,
    WORKING_DIR,
    SESSIONS_DIR,
    MAX_SESSION_MESSAGES,
    MAX_AGENT_STEPS,
    MAX_AUTO_FIX,
    MAX_TOKENS,
    FILE_MUTATING_TOOLS,
    CONTEXT_TRIM_THRESHOLD,
    CONTEXT_KEEP_MESSAGES,
    EXECUTION_ERROR_INDICATORS,
    TIMEOUT_INDICATOR,
    RATE_LIMIT_ERROR,
    RATE_LIMIT_KEYWORD,
    BAD_REQUEST_ERROR,
    INVALID_KEYWORD,
    SERVICE_UNAVAILABLE_ERROR,
    UNAVAILABLE_KEYWORD,
    MODEL_DECOMMISSIONED_INDICATORS,
)

# Core modules
from core import APIKeyManager, load_api_keys, scan_workspace_tree

# UI modules
from ui import (
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
    Spinner,
    spinner,
    reset_action_tracker,
)

# Session modules
from chat_session import SessionManager, list_sessions, delete_session_file

# Tool functions
from functions.get_files_info import get_files_info, schema_get_files_info
from functions.get_file_content import get_file_content, schema_get_file_content
from functions.get_file_outline import get_file_outline, schema_get_file_outline
from functions.write_file import write_file, schema_write_file
from functions.edit_file import edit_file, schema_edit_file
from functions.delete_file import delete_file, schema_delete_file
from functions.run_code import run_code, schema_run_code
from functions.run_command import run_command, schema_run_command
from functions.search_files import search_files, schema_search_files


# =============================================================================
# System Prompt Builder
# =============================================================================


def build_system_prompt():
    """Build the system prompt with current workspace state."""
    tree = scan_workspace_tree(WORKING_DIR)
    return f"""You are CodeCrafter, an AI coding assistant running in a local terminal environment.

CRITICAL: You are running inside a terminal. All your text responses must be PLAIN TEXT.
Do not use any markdown formatting whatsoever. No bold (**), no italic (*), no backticks (`), no headers (#), no horizontal rules (---), no bullet points (- or *), no numbered lists (1. 2. 3.), no code fences (```). Just write plain sentences.
Keep responses concise (1-4 sentences for summaries). Only answer what was asked.

Current workspace contents:
{tree}

TOOLS AVAILABLE:
File: get_files_info, get_file_outline, get_file_content, write_file, edit_file, delete_file
Execution: run_code (auto-detects language from extension), run_command (shell commands)
Search: search_files (grep-like pattern search across files)

RULES:
1. ALWAYS USE TOOLS. Never paste code in your response. Use write_file to create files. Use edit_file to modify existing files.
2. EDIT vs WRITE: For modifying existing files, ALWAYS use edit_file. Only use write_file for new files.
3. Multi-file projects get their own folder. Single scripts stay at workspace root.
4. OUTLINE BEFORE EDIT: On large files, use get_file_outline first, then get_file_content with line ranges, then edit_file.
5. ALWAYS RUN CODE after creating executable files to verify it works.
6. SELF-CORRECTION: If code fails, read the error, fix it (install deps with run_command if needed, fix code with edit_file), and run again. Max 3 retries.
7. DEPENDENCIES: Install required packages before running (pip install, npm install, etc.).
8. GUI APPS (pygame, tkinter, etc.) timeout with run_code. Use run_command with 'start python file.py' on Windows to launch detached.
9. Paths must be RELATIVE to the working directory.
10. Keep responses brief and plain text. Do not repeat code you just wrote.
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
    for i, arg in enumerate(args):
        if arg == "--model" and i + 1 < len(args):
            model_key = args[i + 1]
            if model_key in MODELS:
                selected_model = model_key
            else:
                selected_model = model_key  # Allow any model name directly

    return verbose, selected_model


# =============================================================================
# Main Application
# =============================================================================


def main():
    """Main entry point for CodeCrafter."""
    # Parse CLI flags
    verbose_mode, selected_model = parse_args()
    main_model = MODELS.get(selected_model, selected_model)

    # Initialize API client
    api_keys = load_api_keys()
    key_manager = APIKeyManager(api_keys)
    client = key_manager.get_client()

    # Initialize session manager
    session_mgr = SessionManager()

    # Get user's name
    user_name = get_user_name()

    # Show intro
    show_intro_banner(user_name, session_mgr.current_session_name, main_model)

    if verbose_mode:
        tree_char = "└─"
        print(
            f"  {dim('  ' + tree_char)}  API Keys: {c(str(key_manager.key_count()), Colors.CYAN)} loaded"
        )

    # Show verbose config
    if verbose_mode:
        show_verbose_config(WORKING_DIR, True)

    # Scan workspace
    workspace_tree = scan_workspace_tree(WORKING_DIR)

    # Show restored message
    if session_mgr.messages and verbose_mode:
        print(f"  {dim(Icons.INFO)}  Restored {len(session_mgr.messages)} messages from session")

    # Tool schemas
    available_tools = get_available_tools()

    # =============================================================================
    # Main Agent Loop
    # =============================================================================

    while True:
        prompt_arrow = "›"
        try:
            user_prompt = input(
                f"\n  {c(Icons.PROMPT, Colors.MAGENTA)} {c(user_name, Colors.BOLD)} {c(prompt_arrow, Colors.CYAN)} "
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

        # Input validation
        if not user_prompt.strip():
            continue

        # Reset action dedup tracker for this turn
        reset_action_tracker()

        # Built-in commands
        cmd_lower = user_prompt.strip().lower()

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
            print(f"  {dim('─' * 52)}")
            for i, s in enumerate(sessions):
                marker = c(Icons.ARROW, Colors.CYAN) if i == 0 else " "
                s_name = s["name"]
                s_mod = s["modified"]
                s_msgs = s["messages"]
                info_line = str(s_mod) + "  |  " + str(s_msgs) + " msgs"
                print(f"  {marker}  {c(s_name, Colors.CYAN)}  {dim(info_line)}")
            print()
            continue

        if cmd_lower == "session new":
            new_name = session_mgr.new_session()
            workspace_tree = scan_workspace_tree(WORKING_DIR)
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
                workspace_tree = scan_workspace_tree(WORKING_DIR)
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

        # Add user message
        session_mgr.add_message("user", user_prompt)

        # Agentic Loop
        system_prompt = build_system_prompt()
        auto_fix_count = 0

        for step in range(MAX_AGENT_STEPS):
            if verbose_mode:
                show_verbose_step(step + 1)
            else:
                spinner.start()

            try:
                response = client.chat.completions.create(
                    model=main_model,
                    messages=[{"role": "system", "content": system_prompt}] + session_mgr.get_messages(),
                    tools=available_tools,
                    tool_choice="auto",
                    max_tokens=MAX_TOKENS,
                )
            except Exception as e:
                spinner.stop()
                error_str = str(e)

                # Handle rate limit errors
                if RATE_LIMIT_ERROR in error_str or RATE_LIMIT_KEYWORD in error_str.lower():
                    if key_manager.rotate():
                        client = key_manager.get_client()
                        continue
                    else:
                        show_error("Rate limit reached. Wait a moment and try again.")

                # Handle bad request errors
                elif BAD_REQUEST_ERROR in error_str or INVALID_KEYWORD in error_str.lower():
                    # Check for model decommission
                    if any(ind in error_str.lower() for ind in MODEL_DECOMMISSIONED_INDICATORS):
                        show_error(
                            f"Model '{main_model}' is unavailable or decommissioned. Try a different model with --model flag."
                        )
                        session_mgr.messages.pop()
                        break
                    # Try key rotation
                    if key_manager.rotate():
                        client = key_manager.get_client()
                        continue
                    # Context too large
                    if len(session_mgr.messages) > CONTEXT_TRIM_THRESHOLD:
                        session_mgr.trim_messages()
                        continue
                    else:
                        show_error(
                            "Request too large even after trimming. Type 'exit' to start fresh."
                        )

                # Handle service unavailable
                elif SERVICE_UNAVAILABLE_ERROR in error_str or UNAVAILABLE_KEYWORD in error_str.lower():
                    show_error("Service temporarily unavailable. Try again in a moment.")

                # Unknown error
                else:
                    show_error(f"Model error: {e}")

                session_mgr.messages.pop()
                break

            spinner.stop()

            choice = response.choices[0]
            assistant_message = choice.message

            # Strip thinking blocks from Qwen-QwQ reasoning
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
            session_mgr.add_message(**msg_to_append)

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
                    result = execute_tool(func_name, func_args, WORKING_DIR, verbose_mode)

                    # Show output
                    if not verbose_mode:
                        show_action(func_name, func_args, result)
                    else:
                        is_error = "ERROR" in str(result) or "Error" in str(result)
                        show_verbose_result(str(result), is_error)

                    # Send tool result back to model
                    result_str = (
                        json.dumps(result)
                        if isinstance(result, (dict, list))
                        else str(result)
                    )
                    session_mgr.add_message(
                        role="tool",
                        tool_call_id=tc.id,
                        content=result_str,
                    )

                    # Refresh workspace after file-mutating operations
                    if func_name in FILE_MUTATING_TOOLS:
                        workspace_tree = scan_workspace_tree(WORKING_DIR)

                    # Auto-fix on execution errors
                    if func_name in ("run_code", "run_command") and has_execution_error(result_str):
                        if auto_fix_count < MAX_AUTO_FIX:
                            auto_fix_count += 1
                            if not verbose_mode:
                                show_auto_fix(auto_fix_count, MAX_AUTO_FIX)
                            session_mgr.add_message(
                                role="user",
                                content=(
                                    "The code produced an error. Read the error carefully and fix it:\n"
                                    "- If it's a missing module/package error, install the dependency using run_command "
                                    "(e.g. 'pip install package_name' or 'npm install package_name').\n"
                                    "- If it's a code error, fix it using edit_file.\n"
                                    "Then run the code again."
                                ),
                            )

            # Empty response after stripping
            elif not assistant_content:
                session_mgr.add_message(
                    role="user",
                    content="Please respond using one of your available tools, or give a text answer.",
                )
                continue

            # Final text output
            else:
                content = assistant_content

                # Code-block detection
                if "```" in content and step < MAX_AGENT_STEPS - 2:
                    session_mgr.add_message(
                        role="user",
                        content="Do NOT paste code in your response. Use the write_file tool to create files instead. Create the files now using write_file.",
                    )
                    spinner.stop()
                    continue

                show_agent_response(content)

                # Show token usage
                if hasattr(response, "usage") and response.usage:
                    usage = response.usage
                    total = usage.prompt_tokens + usage.completion_tokens
                    print(
                        f"  {dim(Icons.TOKENS)}  {dim(f'{usage.prompt_tokens:,} in | {usage.completion_tokens:,} out | {total:,} total')}"
                    )

                session_mgr.save()
                break

            # Check for max steps
            if step == MAX_AGENT_STEPS - 1:
                show_warning(f"CodeCrafter reached max steps ({step + 1}). Resetting...")
                session_mgr.clear()
                break

            # Show usage in verbose mode
            if verbose_mode and hasattr(response, "usage") and response.usage:
                usage = response.usage
                show_verbose_tokens(usage.prompt_tokens, usage.completion_tokens)


if __name__ == "__main__":
    main()
