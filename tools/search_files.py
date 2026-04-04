"""Tool: search_files — grep-like workspace search."""

import os
import re

from tools.base import BaseTool

_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".env"}
_BINARY_EXTS = {
    ".pyc", ".pyo", ".exe", ".dll", ".so", ".dylib", ".o", ".obj",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".mp3", ".mp4", ".avi", ".mov", ".wav",
    ".woff", ".woff2", ".ttf", ".eot",
    ".lock", ".map",
}
_MAX_RESULTS = 50


class SearchFilesTool(BaseTool):
    name = "search_files"
    description = (
        "Search through workspace files for a text pattern (like grep). "
        "Returns matching lines with file paths and line numbers, capped at 50 results. "
        "Use this to find where something is defined, imported, or used before editing. "
        "Supports regex patterns and optional file extension filtering."
    )
    parameters = {
        "pattern": {
            "type": "string",
            "description": "The text or regex pattern to search for in file contents.",
        },
        "directory": {
            "type": "string",
            "description": "Subdirectory to scope the search to (relative to workspace root). Default: entire workspace.",
        },
        "file_extension": {
            "type": "string",
            "description": "Optional file extension filter, e.g. '.py' to only search Python files.",
        },
    }
    required = ["pattern"]

    def execute(
        self,
        *,
        pattern: str,
        directory: str = ".",
        file_extension: str | None = None,
        case_sensitive: bool = False,
        **_kw,
    ) -> str:
        search_dir, err = self.dir_must_exist(directory)
        if err:
            return err

        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(pattern, flags)
        except re.error:
            regex = re.compile(re.escape(pattern), flags)

        matches: list[dict] = []

        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]

            for fname in sorted(files):
                _, ext = os.path.splitext(fname)
                if ext.lower() in _BINARY_EXTS:
                    continue
                if file_extension and ext.lower() != file_extension.lower():
                    continue

                file_path = os.path.join(root, fname)
                relative_path = os.path.relpath(file_path, self.working_directory)

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                preview = line.rstrip()[:150]
                                if len(line.rstrip()) > 150:
                                    preview += "..."
                                matches.append({
                                    "file": relative_path,
                                    "line": line_num,
                                    "content": preview,
                                })
                                if len(matches) >= _MAX_RESULTS:
                                    break
                except Exception:
                    continue

                if len(matches) >= _MAX_RESULTS:
                    break
            if len(matches) >= _MAX_RESULTS:
                break

        if not matches:
            scope = f' in "{directory}"' if directory != "." else ""
            ext_note = f" (filtered to {file_extension})" if file_extension else ""
            return f'No matches found for "{pattern}"{scope}{ext_note}'

        output = [f'Found {len(matches)} match(es) for "{pattern}":\n']
        for m in matches:
            output.append(f"  {m['file']}:{m['line']}  {m['content']}")
        if len(matches) == _MAX_RESULTS:
            output.append("\n  ... (results capped at 50 matches)")
        return "\n".join(output)
