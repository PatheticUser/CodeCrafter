"""Transport-agnostic agent loop.

The AgentLoop knows NOTHING about terminals, ANSI codes, or HTTP.
It takes messages and a workspace path, runs the agent loop, and yields results.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Generator, Optional

from openai import OpenAI

from src.core.settings import settings
from src.tools.registry import ToolRegistry


@dataclass
class AgentResponse:
    """A single step in the agent loop — either a text response or tool calls."""

    text: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    is_final: bool = False
    token_usage: Optional[dict[str, int]] = None
    active_model: str = ""
    step: int = 0


class AgentLoop:
    """Transport-agnostic agent loop.

    Designed to work with both CLI (readline input) and API (WebSocket/HTTP streaming).
    Call ``run_turn()`` for a single user turn, or ``run_turn_streaming()`` for
    step-by-step streaming (useful for WebSocket responses).

    Usage:
        agent = AgentLoop(client=openai_client)
        for response in agent.run_turn_streaming(messages, workspace_dir):
            if response.is_final:
                print(response.text)
    """

    def __init__(
        self,
        client: OpenAI,
        model: str = "",
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.client = client
        self.active_model = model or settings.DEFAULT_MODEL
        self.registry = tool_registry or ToolRegistry()

    # ── Public API ────────────────────────────────────────────────────────

    def run_turn(
        self,
        messages: list[dict[str, Any]],
        workspace_dir: str,
    ) -> list[AgentResponse]:
        """Run a full user turn and return all steps.

        Args:
            messages: The conversation history (with system prompt already prepended).
            workspace_dir: Path to the sandboxed working directory.

        Returns:
            List of AgentResponse objects for each step.
        """
        responses: list[AgentResponse] = []
        for response in self.run_turn_streaming(messages, workspace_dir):
            responses.append(response)
        return responses

    def run_turn_streaming(
        self,
        messages: list[dict[str, Any]],
        workspace_dir: str,
    ) -> Generator[AgentResponse, None, None]:
        """Run a user turn with step-by-step streaming.

        Yields an AgentResponse for each step (tool call, text response, etc.).
        The final response will have ``is_final=True``.

        Args:
            messages: The conversation history.
            workspace_dir: Path to the sandboxed working directory.

        Yields:
            AgentResponse for each step.
        """
        system_prompt = self._build_system_prompt(workspace_dir)
        auto_fix_count = 0
        available_tools = self.registry.get_all_schemas()

        for step in range(settings.MAX_AGENT_STEPS):
            try:
                response = self.client.chat.completions.create(
                    model=self.active_model,
                    messages=[{"role": "system", "content": system_prompt}] + messages,
                    tools=available_tools,
                    tool_choice="auto",
                    max_tokens=settings.MAX_TOKENS,
                )
            except Exception as e:
                error_str = str(e)
                yield AgentResponse(
                    text=f"API error: {error_str}",
                    is_final=True,
                    active_model=self.active_model,
                    step=step,
                )
                return

            choice = response.choices[0]
            assistant_message = choice.message

            # Strip <think> blocks from reasoning models
            assistant_content = assistant_message.content or ""
            if "<think>" in assistant_content:
                assistant_content = re.sub(
                    r"<think>.*?</think>", "", assistant_content, flags=re.DOTALL
                ).strip()

            # Token usage tracking
            token_usage = None
            if hasattr(response, "usage") and response.usage:
                usage = response.usage
                token_usage = {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.prompt_tokens + usage.completion_tokens,
                }

            # Handle tool calls
            if assistant_message.tool_calls:
                tool_calls_data = []
                tool_results_data = []

                for tc in assistant_message.tool_calls:
                    func_name = tc.function.name
                    try:
                        func_args = json.loads(tc.function.arguments) or {}
                    except (json.JSONDecodeError, TypeError):
                        func_args = {}

                    result = self.registry.execute(func_name, workspace_dir, **func_args)

                    result_str = (
                        json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                    )

                    tool_calls_data.append({
                        "id": tc.id,
                        "name": func_name,
                        "arguments": func_args,
                    })
                    tool_results_data.append({
                        "tool_call_id": tc.id,
                        "name": func_name,
                        "result": result_str,
                    })

                    # Add tool result to messages for the next LLM call
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })

                    # Auto-fix on execution errors
                    if func_name in ("run_code", "run_command") and self._has_execution_error(result_str):
                        if auto_fix_count < settings.MAX_AUTO_FIX:
                            auto_fix_count += 1
                            messages.append({
                                "role": "user",
                                "content": (
                                    "The code produced an error. Read the error carefully and fix it:\n"
                                    "- If it's a missing module/package error, install the dependency using run_command.\n"
                                    "- If it's a code error, fix it using edit_file.\n"
                                    "Then run the code again."
                                ),
                            })

                yield AgentResponse(
                    tool_calls=tool_calls_data,
                    tool_results=tool_results_data,
                    is_final=False,
                    token_usage=token_usage,
                    active_model=self.active_model,
                    step=step,
                )

            # Empty response after stripping thinking blocks
            elif not assistant_content:
                messages.append({
                    "role": "user",
                    "content": "Please respond using one of your available tools, or give a text answer.",
                })
                continue

            # Final text output
            else:
                content = assistant_content

                # Code-block detection — prevent pasting code instead of using tools
                if "```" in content and step < settings.MAX_AGENT_STEPS - 2:
                    messages.append({
                        "role": "user",
                        "content": (
                            "Do NOT paste code in your response. "
                            "Use the write_file tool to create files instead. "
                            "Create the files now using write_file."
                        ),
                    })
                    continue

                yield AgentResponse(
                    text=content,
                    is_final=True,
                    token_usage=token_usage,
                    active_model=self.active_model,
                    step=step,
                )
                return

            # Check for max steps
            if step == settings.MAX_AGENT_STEPS - 1:
                yield AgentResponse(
                    text=f"Reached max steps ({step + 1}).",
                    is_final=True,
                    active_model=self.active_model,
                    step=step,
                )
                return

    # ── Private Helpers ───────────────────────────────────────────────────

    def _build_system_prompt(self, workspace_dir: str) -> str:
        """Build the system prompt with current workspace state."""
        from src.core.workspace import scan_workspace_tree

        tree = scan_workspace_tree(workspace_dir)
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

    def _has_execution_error(self, result_str: str) -> bool:
        """Detect if a tool result contains an execution error worth auto-fixing."""
        if settings.TIMEOUT_INDICATOR in result_str.lower():
            return False
        for indicator in settings.EXECUTION_ERROR_INDICATORS:
            if indicator in result_str:
                return True
        return False
