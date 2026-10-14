"""Canonical Asynchronous CodingAgent for CodeCrafter.

Decoupled from terminal, CLI, and HTTP transport.
Operates on an abstract Workspace and emits structured AgentEvent instances.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any

from src.core.events import AgentEvent, EventType
from src.core.settings import settings
from src.llm.protocol import LLMProvider, LLMResponse
from src.tools.registry import ToolRegistry
from src.workspace.base import Workspace

logger = logging.getLogger("codecrafter.agent")

AUTO_FIX_INSTRUCTIONS = (
    "The code produced an error. Read the error carefully and fix it:\n"
    "- If it's a missing dependency, install it using run_command.\n"
    "- If it's a code error, fix it using edit_file.\n"
    "Then run the code again."
)

NEED_TOOL_INSTRUCTIONS = (
    "Please respond using one of your available tools, or provide a text answer."
)

CODE_BLOCK_INSTRUCTIONS = (
    "Do NOT paste code directly in your response. Use the write_file tool to write "
    "code files into the workspace instead."
)

SYSTEM_PROMPT_TEMPLATE = """You are CodeCrafter, an expert autonomous AI software engineer.

OUTPUT INSTRUCTION: Plain text explanation only. Never paste markdown code blocks (```) in chat.
Always create and modify files using tools. Keep conversational answers concise (1-3 sentences).

WORKSPACE DIRECTORY TREE:
{workspace_tree}

AVAILABLE TOOLS:
- Files: get_files_info | get_file_outline (inspect structure) | get_file_content (read ranges)
  | write_file (create/overwrite) | edit_file (surgical find & replace) | delete_file
- Execution: run_code (auto-detects .py, .js, .ts, .cpp, .c, .rs, .go, .java)
  | run_command (shell command, uv add, npm test)
- Search: search_files (grep across files)

CRITICAL RULES:
1. NEVER paste code blocks in your text response. Always use write_file or edit_file.
2. For existing files, inspect outline or line ranges first, then edit Surgically.
3. After creating or modifying code, execute run_code or test commands to verify.
4. If execution produces errors, analyze carefully, apply fixes with edit_file, and re-test.
5. All file paths must be relative to the workspace root.
"""


class CodingAgent:
    """Canonical AI coding agent driving multi-step reasoning and workspace execution."""

    def __init__(
        self,
        provider: LLMProvider,
        registry: ToolRegistry | None = None,
    ):
        self.provider = provider
        self.registry = registry or ToolRegistry()

    async def run(
        self,
        prompt: str,
        workspace: Workspace,
        session_id: str,
        run_id: str,
        conversation_history: list[dict[str, Any]] | None = None,
        cancellation_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute agent reasoning loop for a user turn, yielding structured events."""
        sequence = 1

        def make_event(event_type: EventType, data: dict[str, Any]) -> AgentEvent:
            nonlocal sequence
            event = AgentEvent(
                type=event_type,
                run_id=run_id,
                sequence=sequence,
                data=data,
            )
            sequence += 1
            return event

        # Emit start event
        yield make_event(
            EventType.AGENT_STARTED,
            {"prompt": prompt, "session_id": session_id, "workspace_id": workspace.workspace_id},
        )

        messages: list[dict[str, Any]] = list(conversation_history or [])
        messages.append({"role": "user", "content": prompt})

        # Build initial system prompt with live workspace tree
        workspace_tree = await workspace.scan_tree()
        system_prompt = self._build_system_prompt(workspace_tree)

        available_tools = self.registry.get_all_schemas()
        auto_fix_count = 0

        for step in range(settings.MAX_AGENT_STEPS):
            # Check for cancellation
            if cancellation_event and cancellation_event.is_set():
                yield make_event(
                    EventType.AGENT_CANCELLED,
                    {"step": step, "reason": "Execution cancelled by user."},
                )
                return

            # Safe progress indicator — no hidden reasoning traces leaked
            yield make_event(
                EventType.AGENT_THINKING,
                {"step": step + 1, "status": "Analyzing task and context..."},
            )

            # LLM completion
            current_messages = [{"role": "system", "content": system_prompt}] + messages
            response: LLMResponse = await self.provider.complete(
                messages=current_messages,
                tools=available_tools,
                temperature=settings.LLM_TEMPERATURE,
            )

            # Check for cancellation post-LLM call
            if cancellation_event and cancellation_event.is_set():
                yield make_event(
                    EventType.AGENT_CANCELLED,
                    {"step": step, "reason": "Execution cancelled by user."},
                )
                return

            if response.error:
                yield make_event(
                    EventType.AGENT_FAILED, {"step": step + 1, "error": response.error}
                )
                return

            # Strip <think> blocks from reasoning models
            assistant_content = response.content or ""
            if "<think>" in assistant_content:
                assistant_content = re.sub(
                    r"<think>.*?</think>", "", assistant_content, flags=re.DOTALL
                ).strip()

            # Handle tool calls
            if response.tool_calls:
                # 1. Append assistant tool-call message in correct protocol order
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": assistant_content or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": tc.raw_arguments or json.dumps(tc.arguments),
                            },
                        }
                        for tc in response.tool_calls
                    ],
                }
                messages.append(assistant_msg)

                # 2. Execute each requested tool call against the workspace
                for tc in response.tool_calls:
                    if cancellation_event and cancellation_event.is_set():
                        yield make_event(
                            EventType.AGENT_CANCELLED,
                            {"step": step, "reason": "Execution cancelled by user."},
                        )
                        return

                    yield make_event(
                        EventType.TOOL_STARTED,
                        {"tool": tc.name, "tool_call_id": tc.id, "arguments": tc.arguments},
                    )

                    tool_result = await self.registry.execute(tc.name, workspace, **tc.arguments)

                    # Extract string representation and diff if available
                    diff_text = None
                    if isinstance(tool_result, dict):
                        diff_text = tool_result.get("diff")
                        result_str = tool_result.get("result", json.dumps(tool_result))
                    else:
                        result_str = str(tool_result)

                    is_error = (
                        "error" in result_str.lower() or "compilation failed" in result_str.lower()
                    )

                    if is_error:
                        yield make_event(
                            EventType.TOOL_FAILED,
                            {"tool": tc.name, "tool_call_id": tc.id, "error": result_str},
                        )
                    else:
                        yield make_event(
                            EventType.TOOL_COMPLETED,
                            {
                                "tool": tc.name,
                                "tool_call_id": tc.id,
                                "result": result_str,
                                "diff": diff_text,
                            },
                        )

                    # File-level events
                    file_path = tc.arguments.get("file_path") or tc.arguments.get("path")
                    if file_path:
                        if tc.name == "write_file" and not is_error:
                            yield make_event(EventType.FILE_CREATED, {"path": file_path})
                        elif tc.name == "edit_file" and not is_error:
                            yield make_event(
                                EventType.FILE_MODIFIED, {"path": file_path, "diff": diff_text}
                            )
                        elif tc.name == "delete_file" and not is_error:
                            yield make_event(EventType.FILE_DELETED, {"path": file_path})

                    # Command execution output event
                    if tc.name in ("run_code", "run_command"):
                        yield make_event(
                            EventType.EXECUTION_OUTPUT,
                            {
                                "tool": tc.name,
                                "output": result_str,
                                "exit_code": 1 if is_error else 0,
                            },
                        )

                    # Append tool response message
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result_str,
                        }
                    )

                    # Refresh system prompt workspace tree if file mutation occurred
                    if tc.name in settings.FILE_MUTATING_TOOLS and not is_error:
                        tree = await workspace.scan_tree()
                        system_prompt = self._build_system_prompt(tree)

                    # Auto-fix error detection
                    if tc.name in ("run_code", "run_command") and self._has_execution_error(
                        result_str
                    ):
                        if auto_fix_count < settings.MAX_AUTO_FIX:
                            auto_fix_count += 1
                            messages.append(
                                {
                                    "role": "user",
                                    "content": AUTO_FIX_INSTRUCTIONS,
                                }
                            )

            elif not assistant_content:
                # Empty response: prompt model to produce text or use a tool
                messages.append(
                    {
                        "role": "user",
                        "content": NEED_TOOL_INSTRUCTIONS,
                    }
                )
                continue

            else:
                # Text response produced
                if "```" in assistant_content and step < settings.MAX_AGENT_STEPS - 2:
                    # Model pasted markdown code instead of using write_file
                    messages.append(
                        {
                            "role": "user",
                            "content": CODE_BLOCK_INSTRUCTIONS,
                        }
                    )
                    continue

                # Final message
                messages.append({"role": "assistant", "content": assistant_content})
                yield make_event(
                    EventType.AGENT_MESSAGE,
                    {"content": assistant_content, "token_usage": response.usage},
                )
                yield make_event(
                    EventType.AGENT_COMPLETED,
                    {
                        "step": step + 1,
                        "token_usage": response.usage,
                        "finish_reason": response.finish_reason,
                    },
                )
                return

        # Max steps exhausted
        yield make_event(
            EventType.AGENT_COMPLETED,
            {
                "step": settings.MAX_AGENT_STEPS,
                "warning": "Reached maximum allowed steps without final text.",
            },
        )

    def _build_system_prompt(self, workspace_tree: str) -> str:
        """Construct compact workspace-aware system instructions."""
        return SYSTEM_PROMPT_TEMPLATE.format(workspace_tree=workspace_tree)

    def _has_execution_error(self, result_str: str) -> bool:
        """Check if output contains actionable execution errors, excluding timeouts."""
        if settings.TIMEOUT_INDICATOR in result_str.lower():
            return False
        return any(indicator in result_str for indicator in settings.EXECUTION_ERROR_INDICATORS)
