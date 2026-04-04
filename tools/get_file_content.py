"""Tool: get_file_content — read a file with optional line-range support."""

import os

from tools.base import BaseTool


class GetFileContentTool(BaseTool):
    name = "get_file_content"
    description = (
        "Read the contents of a file. For small files (<=300 lines), returns the full file. "
        "For large files, returns the first 50 and last 20 lines with a hint to use "
        "start_line/end_line for specific ranges. "
        "Use get_file_outline first to understand file structure before reading large files."
    )
    parameters = {
        "file_path": {
            "type": "string",
            "description": "Relative path of the file to read.",
        },
        "start_line": {
            "type": "integer",
            "description": "Optional 1-based starting line number to read from.",
        },
        "end_line": {
            "type": "integer",
            "description": "Optional 1-based ending line number to read to (inclusive).",
        },
    }
    required = ["file_path"]

    def execute(self, *, file_path: str, start_line: int | None = None, end_line: int | None = None, **_kw) -> str:
        abs_path, err = self.file_must_exist(file_path)
        if err:
            return err

        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            return f"Error: {e}"

        total_lines = len(lines)

        # Specific line range requested
        if start_line is not None or end_line is not None:
            s = max(1, start_line or 1)
            e = min(total_lines, end_line or total_lines)
            if s > total_lines:
                return f"Error: start_line {s} exceeds file length ({total_lines} lines)"
            selected = lines[s - 1 : e]
            header = f"[{file_path} — lines {s}-{e} of {total_lines}]\n"
            numbered = "".join(f"L{i}: {line}" for i, line in enumerate(selected, s))
            return header + numbered

        # Small files: return everything
        if total_lines <= 300:
            return f"[{file_path} — {total_lines} lines]\n" + "".join(lines)

        # Large files: head + tail + hint
        head = "".join(f"L{i}: {line}" for i, line in enumerate(lines[:50], 1))
        tail = "".join(
            f"L{i}: {line}" for i, line in enumerate(lines[-20:], total_lines - 19)
        )
        hint = (
            f"\n\n... ({total_lines - 70} lines omitted) ...\n\n"
            f"File has {total_lines} lines. Use start_line/end_line to read specific sections, "
            f"or use get_file_outline to see the file structure.\n\n"
        )
        return f"[{file_path} — {total_lines} lines (showing head + tail)]\n{head}{hint}{tail}"
