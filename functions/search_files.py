import os
import re

from functions._security import validate_directory


def search_files(
    working_directory, pattern, directory=".", file_extension=None, case_sensitive=False
):
    """
    Search through workspace files for a text pattern. Returns matching lines
    with file paths and line numbers, capped at 50 results.

    Args:
        working_directory: The sandboxed working directory
        pattern: Text or regex pattern to search for
        directory: Subdirectory to scope the search (default: workspace root)
        file_extension: Optional filter, e.g. ".py" (include the dot)
        case_sensitive: Whether the search is case-sensitive (default: False)

    Returns:
        Formatted string of matches, or error message
    """
    # Security: path traversal check
    err = validate_directory(working_directory, directory)
    if err:
        return err

    working_dir_abs = os.path.realpath(working_directory)
    search_dir = os.path.realpath(os.path.join(working_directory, directory))

    if not os.path.isdir(search_dir):
        return f'Error: Directory not found: "{directory}"'

    # --- Compile pattern ---
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error:
        # Fall back to literal search if pattern is not valid regex
        regex = re.compile(re.escape(pattern), flags)

    # --- Walk and search ---
    matches = []
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".env"}
    # Common binary extensions to skip
    binary_exts = {
        ".pyc",
        ".pyo",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".o",
        ".obj",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".svg",
        ".zip",
        ".tar",
        ".gz",
        ".rar",
        ".7z",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wav",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".lock",
        ".map",
    }

    for root, dirs, files in os.walk(search_dir):
        # Skip hidden/irrelevant directories
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]

        for fname in sorted(files):
            # Skip binary files
            _, ext = os.path.splitext(fname)
            if ext.lower() in binary_exts:
                continue

            # Apply extension filter
            if file_extension and ext.lower() != file_extension.lower():
                continue

            file_path = os.path.join(root, fname)
            relative_path = os.path.relpath(file_path, working_dir_abs)

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            line_preview = line.rstrip()
                            if len(line_preview) > 150:
                                line_preview = line_preview[:150] + "..."
                            matches.append(
                                {
                                    "file": relative_path,
                                    "line": line_num,
                                    "content": line_preview,
                                }
                            )
                            if len(matches) >= 50:
                                break
            except Exception:
                continue  # Skip files that can't be read

            if len(matches) >= 50:
                break
        if len(matches) >= 50:
            break

    # --- Format output ---
    if not matches:
        scope = f' in "{directory}"' if directory != "." else ""
        ext_note = f" (filtered to {file_extension})" if file_extension else ""
        return f'No matches found for "{pattern}"{scope}{ext_note}'

    output_lines = [f'Found {len(matches)} match(es) for "{pattern}":\n']
    for m in matches:
        output_lines.append(f"  {m['file']}:{m['line']}  {m['content']}")

    if len(matches) == 50:
        output_lines.append("\n  ... (results capped at 50 matches)")

    return "\n".join(output_lines)


# --- OpenAI-compatible tool schema ---
schema_search_files = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": "Search files for a pattern (grep). Returns file:line matches, capped at 50. Supports regex and extension filter.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Text or regex pattern to search for.",
                },
                "directory": {
                    "type": "string",
                    "description": "Subdirectory to scope search. Default: workspace root.",
                },
                "file_extension": {
                    "type": "string",
                    "description": "Filter by extension, e.g. '.py'.",
                },
            },
            "required": ["pattern"],
        },
    },
}
