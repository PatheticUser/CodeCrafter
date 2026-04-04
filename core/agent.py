"""AgentLoop — core agentic step loop for CodeCrafter.

Inspired by Claude Code's QueryEngine — this module owns the entire
LLM ↔ Tool interaction cycle, separated from CLI/UI concerns.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from config import (
    WORKING_DIR,
    MAX_AGENT_STEPS,
    MAX_AUTO_FIX,
    MAX_TOKENS,
    CONTEXT_TRIM_THRESHOLD,
)
from core.errors import has_execution_error, should_fallback
from core.workspace import scan_workspace_tree
from services.logger import logger
from ui import (
    c, Colors, Icons, dim,
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
    spinner,
    reset_action_tracker,
)

if TYPE_CHECKING:
    from core.api_manager import OllamaClient
    from chat_session.manager import SessionManager
    from tools import ToolRegistry


# =============================================================================
# System Prompt
# =============================================================================

def build_system_prompt() -> str:
    """Build the system prompt with current workspace state."""
    tree = scan_workspace_tree(WORKING_DIR)
    return f"""You are CodeCrafter, an AI coding assistant running in a local terminal environment.

CRITICAL: You are running in an advanced terminal that supports full Markdown rendering.
Format responses beautifully using Markdown (bold, italic, headers, bullet points, syntax-highlighted code fences).
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
# Auto-fix prompt
# =============================================================================

_AUTO_FIX_PROMPT = (
    "The code produced an error. Read the error carefully and fix it:\n"
    "- If it's a missing module/package error, install the dependency using run_command "
    "(e.g. 'pip install package_name' or 'npm install package_name').\n"
    "- If it's a code error, fix it using edit_file.\n"
    "Then run the code again."
)


# =============================================================================
# AgentLoop
# =============================================================================

class AgentLoop:
    """Runs the agentic tool-calling loop for a single user turn.

    One instance is created per user turn. It manages the multi-step
    LLM ↔ tool cycle, model fallback, auto-fix, and context trimming.
    """

    def __init__(
        self,
        ollama: OllamaClient,
        session_mgr: SessionManager,
        tool_registry: ToolRegistry,
        verbose: bool = False,
    ) -> None:
        self.ollama = ollama
        self.client = ollama.get_client()
        self.session_mgr = session_mgr
        self.tools = tool_registry
        self.verbose = verbose

    def run(self) -> None:
        """Execute the agentic loop for the current turn."""
        system_prompt = build_system_prompt()
        schemas = self.tools.get_schemas()
        auto_fix_count = 0

        # Reset to primary model at the start of each turn
        self.ollama.reset()
        active_model = self.ollama.active_model

        for step in range(MAX_AGENT_STEPS):
            if self.verbose:
                show_verbose_step(step + 1)
            else:
                spinner.start()

            # --- LLM call ---
            try:
                response = self.client.chat.completions.create(
                    model=active_model,
                    messages=[{"role": "system", "content": system_prompt}]
                    + self.session_mgr.get_messages(),
                    tools=schemas,
                    tool_choice="auto",
                    max_tokens=MAX_TOKENS,
                )
            except Exception as e:
                spinner.stop()
                active_model = self._handle_api_error(e, active_model)
                if active_model is None:
                    return
                continue

            spinner.stop()

            choice = response.choices[0]
            message = choice.message

            # Strip thinking blocks from reasoning models
            content = self._strip_thinking(message.content or "")

            # Add assistant response to session
            self._record_assistant(message, content)

            # --- Tool calls ---
            if message.tool_calls:
                for tc in message.tool_calls:
                    func_name = tc.function.name
                    func_args = self._parse_args(tc.function.arguments)

                    if self.verbose:
                        file_path = func_args.get("file_path", "")
                        show_function_call(
                            func_name,
                            file_path or func_args.get("command", "")
                            or func_args.get("pattern", "") or "context",
                        )
                        show_verbose_function(func_name, func_args)

                    # Execute tool
                    result = self.tools.execute(func_name, **func_args)

                    # Display
                    if not self.verbose:
                        show_action(func_name, func_args, result)
                    else:
                        is_error = "ERROR" in str(result) or "Error" in str(result)
                        show_verbose_result(str(result), is_error)

                    # Feed result back to session
                    result_str = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                    self.session_mgr.add_message(
                        role="tool", tool_call_id=tc.id, content=result_str,
                    )

                    # Refresh workspace on mutating ops
                    if self.tools.is_mutating(func_name):
                        scan_workspace_tree(WORKING_DIR)

                    # Auto-fix on execution errors
                    if self.tools.is_auto_fixable(func_name) and has_execution_error(result_str):
                        if auto_fix_count < MAX_AUTO_FIX:
                            auto_fix_count += 1
                            if not self.verbose:
                                show_auto_fix(auto_fix_count, MAX_AUTO_FIX)
                            self.session_mgr.add_message(role="user", content=_AUTO_FIX_PROMPT)

            # --- Empty response (model confusion) ---
            elif not content:
                self.session_mgr.add_message(
                    role="user",
                    content="Please respond using one of your available tools, or give a text answer.",
                )
                continue

            # --- Final text output ---
            else:
                # Code-block leak detection (softened for markdown capabilities)
                if "```python" in content or "```javascript" in content or "```ts" in content:
                    if step < MAX_AGENT_STEPS - 2 and not (message.tool_calls and "write_file" in [tc.function.name for tc in message.tool_calls]):
                        # Just a slight reminder if they dump too much code, let it pass though
                        pass 

                show_agent_response(content)

                # Token usage display
                if hasattr(response, "usage") and response.usage:
                    usage = response.usage
                    total = usage.prompt_tokens + usage.completion_tokens
                    from ui.display import console
                    console.print(
                        f"  [dim]{Icons.TOKENS}[/]  "
                        f"[dim]{usage.prompt_tokens:,} in | {usage.completion_tokens:,} out | {total:,} total[/]"
                    )

                self.session_mgr.save()
                return

            # Max steps guard
            if step == MAX_AGENT_STEPS - 1:
                show_warning(f"CodeCrafter reached max steps ({step + 1}). Saving and resetting...")
                self.session_mgr.save()  # Save before clearing
                self.session_mgr.clear()
                return

            # Verbose token display
            if self.verbose and hasattr(response, "usage") and response.usage:
                show_verbose_tokens(response.usage.prompt_tokens, response.usage.completion_tokens)

            # Periodic save every 5 steps (crash safety)
            if step > 0 and step % 5 == 0:
                self.session_mgr.save()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _handle_api_error(self, error: Exception, active_model: str) -> str | None:
        """Handle API errors with fallback logic. Returns new model name or None to abort."""
        error_str = str(error)
        logger.error("API error on model '%s': %s", active_model, error_str)

        # Try model fallback on recoverable errors
        if should_fallback(error_str):
            new_model = self.ollama.fallback()
            if new_model:
                print(
                    f"  {c(Icons.INFO, Colors.DIM)}  "
                    f"{c(active_model, Colors.DIM)} failed, switching to "
                    f"{c(new_model, Colors.CYAN)}"
                )
                return new_model

        # Context too large — trim and retry
        if "400" in error_str and len(self.session_mgr.messages) > CONTEXT_TRIM_THRESHOLD:
            self.session_mgr.trim_messages()
            return active_model

        # Connection error
        if "connection" in error_str.lower() or "refused" in error_str.lower():
            show_error("Cannot connect to Ollama. Make sure it is running: ollama serve")
        else:
            show_error(f"All models failed: {error}")

        self.session_mgr.messages.pop()
        return None

    @staticmethod
    def _strip_thinking(content: str) -> str:
        if "<think>" in content:
            return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return content

    @staticmethod
    def _parse_args(arguments_json: str) -> dict:
        try:
            return json.loads(arguments_json) or {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def _record_assistant(self, message, content: str) -> None:
        """Add the assistant's response to session history."""
        msg: dict = {"role": "assistant", "content": content}
        if message.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        self.session_mgr.add_message(**msg)
