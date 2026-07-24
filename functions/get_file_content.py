import os

from functions._security import validate_path


def get_file_content(working_directory, file_path, start_line=None, end_line=None):
    """
    Reads a file within the working_directory safely.
    Supports reading specific line ranges for token efficiency.

    Args:
        working_directory: The sandboxed working directory
        file_path: Relative path to the file to read
        start_line: Optional 1-based start line number
        end_line: Optional 1-based end line number

    Returns:
        File contents (possibly with range info) or error string
    """
    # Security: path traversal check
    err = validate_path(working_directory, file_path)
    if err:
        return err

    target_file_abs = os.path.realpath(os.path.join(working_directory, file_path))

    # 2. Validate file exists
    if not os.path.isfile(target_file_abs):
        return f'Error: File not found: "{file_path}"'

    try:
        with open(target_file_abs, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        return f"Error: {e}"

    total_lines = len(lines)

    # --- Specific line range requested ---
    if start_line is not None or end_line is not None:
        s = max(1, start_line or 1)
        e = min(total_lines, end_line or total_lines)
        if s > total_lines:
            return f"Error: start_line {s} exceeds file length ({total_lines} lines)"
        selected = lines[s - 1 : e]
        header = f"[{file_path} — lines {s}-{e} of {total_lines}]\n"
        numbered = "".join(f"L{i}: {line}" for i, line in enumerate(selected, s))
        return header + numbered

    # --- No range: auto-decide based on file size ---
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
    return (
        f"[{file_path} — {total_lines} lines (showing head + tail)]\n{head}{hint}{tail}"
    )


# --- OpenAI-compatible tool schema ---
schema_get_file_content = {
    "type": "function",
    "function": {
        "name": "get_file_content",
        "description": "Read a file. Small files (<300 lines) return fully. Large files show head+tail with line ranges.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "File path relative to workspace.",
                },
                "start_line": {
                    "type": "integer",
                    "description": "1-based start line (optional).",
                },
                "end_line": {
                    "type": "integer",
                    "description": "1-based end line inclusive (optional).",
                },
            },
            "required": ["file_path"],
        },
    },
}
