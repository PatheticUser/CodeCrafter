"""Local filesystem workspace implementation."""

from __future__ import annotations

import asyncio
import difflib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.workspace.base import CommandResult, Workspace
from src.workspace.security import is_command_blocked, resolve_safe_path


class LocalWorkspace(Workspace):
    """Local workspace operating on a designated host directory with strict isolation."""

    def __init__(
        self,
        workspace_id: str,
        root_dir: Path | str,
        command_timeout: int = 60,
        max_output_bytes: int = 50000,
    ):
        self._workspace_id = workspace_id
        self._root_dir = Path(root_dir).resolve()
        self._command_timeout = command_timeout
        self._max_output_bytes = max_output_bytes
        self._root_dir.mkdir(parents=True, exist_ok=True)

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    async def list_files(self, directory: str = ".") -> list[dict[str, Any]]:
        """List files with sizes and modification dates."""
        target_dir = resolve_safe_path(self._root_dir, directory, must_exist=True)
        if not target_dir.is_dir():
            raise NotADirectoryError(f"'{directory}' is not a directory")

        def _scan() -> list[dict[str, Any]]:
            items: list[dict[str, Any]] = []
            for root, dirs, files in os.walk(target_dir):
                # Filter out hidden and build directories
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in {"node_modules", "__pycache__", ".venv", "venv", ".git"}
                ]
                for f in sorted(files):
                    if f.startswith(".") or f.endswith(".pyc"):
                        continue
                    file_path = Path(root) / f
                    try:
                        rel_path = file_path.relative_to(self._root_dir).as_posix()
                        stat = file_path.stat()
                        items.append(
                            {
                                "path": rel_path,
                                "size_bytes": stat.st_size,
                                "size_kb": round(stat.st_size / 1024, 2),
                                "modified": datetime.fromtimestamp(stat.st_mtime).strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                            }
                        )
                    except Exception:
                        continue
            return items

        return await asyncio.to_thread(_scan)

    async def read_file(
        self,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        """Read full file or slice of lines."""
        target_file = resolve_safe_path(self._root_dir, file_path, must_exist=True)
        if not target_file.is_file():
            raise FileNotFoundError(f"File not found: '{file_path}'")

        def _read() -> str:
            with open(target_file, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            if start_line is not None or end_line is not None:
                s = max(1, start_line or 1)
                e = min(total_lines, end_line or total_lines)
                if s > total_lines:
                    return f"Error: start_line {s} exceeds file length ({total_lines} lines)"
                selected = lines[s - 1 : e]
                header = f"[{file_path} — lines {s}-{e} of {total_lines}]\n"
                numbered = "".join(f"L{i}: {line}" for i, line in enumerate(selected, s))
                return header + numbered

            if total_lines <= 300:
                return f"[{file_path} — {total_lines} lines]\n" + "".join(lines)

            head = "".join(f"L{i}: {line}" for i, line in enumerate(lines[:50], 1))
            tail = "".join(f"L{i}: {line}" for i, line in enumerate(lines[-20:], total_lines - 19))
            hint = (
                f"\n\n... ({total_lines - 70} lines omitted) ...\n\n"
                f"File has {total_lines} lines. Use start_line/end_line to read sections.\n\n"
            )
            return f"[{file_path} — {total_lines} lines (showing head + tail)]\n{head}{hint}{tail}"

        return await asyncio.to_thread(_read)

    async def write_file(self, file_path: str, content: str) -> str:
        """Write content to file, creating parent directories as necessary."""
        target_file = resolve_safe_path(self._root_dir, file_path, must_exist=False)

        def _write() -> str:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(content)
            return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'

        return await asyncio.to_thread(_write)

    async def edit_file(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
    ) -> dict[str, Any] | str:
        """Targeted string replacement with diff preview."""
        target_file = resolve_safe_path(self._root_dir, file_path, must_exist=True)

        def _edit() -> dict[str, Any] | str:
            with open(target_file, encoding="utf-8", errors="replace") as f:
                content = f.read()

            count = content.count(old_content)
            if count == 0:
                lines = content.splitlines()
                total = len(lines)
                preview = (
                    "\n".join(lines[:15])
                    if total <= 15
                    else "\n".join(lines[:15])
                    + f"\n... ({total - 25} lines omitted) ...\n"
                    + "\n".join(lines[-10:])
                )
                return (
                    f'Error: Could not find specified old_content in "{file_path}".\n'
                    f"File preview:\n```\n{preview}\n```\n"
                    "Verify file content with get_file_content before editing."
                )

            new_file_content = (
                content.replace(old_content, new_content, 1)
                if count > 1
                else content.replace(old_content, new_content)
            )
            warning = (
                f" (Warning: found {count} occurrences, replaced only first)" if count > 1 else ""
            )

            # Unified diff
            diff = difflib.unified_diff(
                content.splitlines(),
                new_file_content.splitlines(),
                n=2,
                lineterm="",
            )
            diff_lines = [line for line in diff if not line.startswith(("---", "+++", "@@"))]
            diff_text = "\n".join(diff_lines)

            with open(target_file, "w", encoding="utf-8") as f:
                f.write(new_file_content)

            old_lines = old_content.count("\n") + 1
            new_lines = new_content.count("\n") + 1
            result = (
                f'Successfully edited "{file_path}" — replaced '
                f"{old_lines} line(s) with {new_lines} line(s){warning}"
            )
            return {"result": result, "diff": diff_text}

        return await asyncio.to_thread(_edit)

    async def delete_file(self, file_path: str) -> str:
        """Delete file inside workspace."""
        target_file = resolve_safe_path(self._root_dir, file_path, must_exist=True)
        if not target_file.is_file():
            raise FileNotFoundError(f"'{file_path}' is not a regular file")

        def _delete() -> str:
            target_file.unlink()
            return f'Successfully deleted "{file_path}".'

        return await asyncio.to_thread(_delete)

    async def search_files(
        self,
        pattern: str,
        directory: str = ".",
        file_extension: str | None = None,
        case_sensitive: bool = False,
    ) -> str:
        """Search regex/pattern in workspace files."""
        search_dir = resolve_safe_path(self._root_dir, directory, must_exist=True)

        def _search() -> str:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error:
                regex = re.compile(re.escape(pattern), flags)

            matches: list[dict[str, Any]] = []
            skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".env"}
            binary_exts = {
                ".pyc",
                ".exe",
                ".dll",
                ".so",
                ".png",
                ".jpg",
                ".jpeg",
                ".zip",
                ".tar",
                ".gz",
                ".pdf",
                ".lock",
                ".ico",
                ".bin",
            }

            for root, dirs, files in os.walk(search_dir):
                dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
                for fname in sorted(files):
                    _, ext = os.path.splitext(fname)
                    if ext.lower() in binary_exts:
                        continue
                    if file_extension and ext.lower() != file_extension.lower():
                        continue
                    f_path = Path(root) / fname
                    try:
                        rel = f_path.relative_to(self._root_dir).as_posix()
                        with open(f_path, encoding="utf-8", errors="ignore") as f:
                            for idx, line in enumerate(f, 1):
                                if regex.search(line):
                                    preview = line.strip()
                                    if len(preview) > 150:
                                        preview = preview[:150] + "..."
                                    matches.append({"file": rel, "line": idx, "content": preview})
                                    if len(matches) >= 50:
                                        break
                    except Exception:
                        continue
                    if len(matches) >= 50:
                        break
                if len(matches) >= 50:
                    break

            if not matches:
                scope = f' in "{directory}"' if directory != "." else ""
                ext_note = f" (filtered to {file_extension})" if file_extension else ""
                return f'No matches found for "{pattern}"{scope}{ext_note}'

            output = [f'Found {len(matches)} match(es) for "{pattern}":\n']
            for m in matches:
                output.append(f"  {m['file']}:{m['line']}  {m['content']}")
            if len(matches) == 50:
                output.append("\n  ... (results capped at 50 matches)")
            return "\n".join(output)

        return await asyncio.to_thread(_search)

    async def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
        """Run command on local host within workspace directory with timeout and safety checks."""
        if is_command_blocked(command):
            return CommandResult(
                exit_code=1,
                stdout="",
                stderr="SecurityError: Command matched high-risk security blocklist.",
            )

        cmd_timeout = timeout or self._command_timeout
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self._root_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=cmd_timeout,
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")[: self._max_output_bytes]
            stderr = stderr_bytes.decode("utf-8", errors="replace")[: self._max_output_bytes]
            return CommandResult(
                exit_code=proc.returncode if proc.returncode is not None else 0,
                stdout=stdout,
                stderr=stderr,
                timed_out=False,
            )
        except TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            return CommandResult(
                exit_code=124,
                stdout="",
                stderr=f"Command timed out after {cmd_timeout} seconds",
                timed_out=True,
            )
        except Exception as e:
            return CommandResult(
                exit_code=1,
                stdout="",
                stderr=f"Failed to execute command: {e}",
            )

    async def get_file_outline(self, file_path: str) -> str:
        """Generate outline (classes, functions, imports)."""
        target_file = resolve_safe_path(self._root_dir, file_path, must_exist=True)

        def _outline() -> str:
            with open(target_file, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            total_lines = len(lines)
            size_kb = round(target_file.stat().st_size / 1024, 1)
            ext = target_file.suffix.lower()
            header = f"File: {file_path} ({total_lines} lines, {size_kb} KB)\n"

            if total_lines <= 50:
                return header + "\n" + "".join(lines)

            imports: list[str] = []
            structures: list[str] = []

            for i, line in enumerate(lines, 1):
                stripped = line.rstrip()
                if not stripped or stripped.startswith("#!"):
                    continue
                if ext in (".py", ".pyw"):
                    if stripped.startswith(("import ", "from ")):
                        imports.append(f"  L{i}: {stripped}")
                    elif re.match(r"^(class\s+\w+[^:]*:)", stripped):
                        structures.append(f"  L{i}: {stripped}")
                    elif re.match(r"^(\s*)(def\s+\w+\s*\([^)]*\)[^:]*:)", stripped):
                        structures.append(f"  L{i}: {stripped}")
                elif ext in (".js", ".ts", ".jsx", ".tsx"):
                    if stripped.startswith("import ") or (
                        "require(" in stripped and stripped.startswith(("const ", "let "))
                    ):
                        imports.append(f"  L{i}: {stripped}")
                    elif re.match(r"^((?:export\s+)?class\s+\w+[^{]*)", stripped):
                        structures.append(f"  L{i}: {stripped}")
                    elif re.match(
                        r"^((?:export\s+)?(?:async\s+)?function\s+\w+\s*\([^)]*\))", stripped
                    ):
                        structures.append(f"  L{i}: {stripped}")

            output = [header]
            if imports:
                output.append("Imports:")
                output.extend(imports[:20])
                if len(imports) > 20:
                    output.append(f"  ... ({len(imports) - 20} more imports)")
                output.append("")
            if structures:
                output.append("Structure:")
                output.extend(structures)
                output.append("")
            if not imports and not structures:
                output.append("Preview (first 10 lines):")
                for i, line in enumerate(lines[:10], 1):
                    output.append(f"  L{i}: {line.rstrip()}")
            return "\n".join(output)

        return await asyncio.to_thread(_outline)

    async def scan_tree(self) -> str:
        """Scan workspace and generate compact visual directory tree."""

        def _tree() -> str:
            skip_dirs = {
                "node_modules",
                "__pycache__",
                ".venv",
                "venv",
                ".git",
                "dist",
                "build",
                ".next",
                "out",
                "target",
                ".mypy_cache",
                ".pytest_cache",
                ".ruff_cache",
            }
            max_items = 50
            lines: list[str] = []
            total_files = 0
            for root, dirs, files in os.walk(self._root_dir):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in skip_dirs]
                level = os.path.relpath(root, self._root_dir)
                if level == ".":
                    for f in sorted(files):
                        if f.startswith(".") or f.endswith(".pyc"):
                            continue
                        total_files += 1
                        if len(lines) < max_items:
                            sz = (Path(root) / f).stat().st_size
                            lines.append(f"{f} ({sz:,}B)")
                else:
                    indent = "  " * level.count(os.sep)
                    if len(lines) < max_items:
                        lines.append(f"{indent}{os.path.basename(root)}/")
                    for f in sorted(files):
                        if f.startswith(".") or f.endswith(".pyc"):
                            continue
                        total_files += 1
                        if len(lines) < max_items:
                            sz = (Path(root) / f).stat().st_size
                            lines.append(f"{indent}  {f} ({sz:,}B)")
            res = "\n".join(lines) if lines else "(empty workspace)"
            if total_files > max_items:
                res += f"\n... ({total_files - max_items:,} more items)"
            return res

        return await asyncio.to_thread(_tree)
