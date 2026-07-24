"""Tool implementations for CodeCrafter agent.

Each tool is a pure function that takes a workspace path and arguments,
and returns a string result. Tools are self-contained and transport-agnostic.
"""

from src.tools.delete_file import delete_file, schema_delete_file
from src.tools.edit_file import edit_file, schema_edit_file
from src.tools.get_file_content import get_file_content, schema_get_file_content
from src.tools.get_file_outline import get_file_outline, schema_get_file_outline

# Schemas for LLM tool definitions
from src.tools.get_files_info import get_files_info, schema_get_files_info
from src.tools.registry import ToolRegistry
from src.tools.run_code import run_code, schema_run_code
from src.tools.run_command import run_command, schema_run_command
from src.tools.search_files import schema_search_files, search_files
from src.tools.write_file import schema_write_file, write_file

__all__ = [
    "get_files_info",
    "get_file_content",
    "get_file_outline",
    "write_file",
    "edit_file",
    "delete_file",
    "run_code",
    "run_command",
    "search_files",
    # Schemas
    "schema_get_files_info",
    "schema_get_file_content",
    "schema_get_file_outline",
    "schema_write_file",
    "schema_edit_file",
    "schema_delete_file",
    "schema_run_code",
    "schema_run_command",
    "schema_search_files",
    # Registry
    "ToolRegistry",
]
