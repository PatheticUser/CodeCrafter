"""Tool: get_file_outline — token-efficient file structure overview."""

import os
import re

from tools.base import BaseTool


class GetFileOutlineTool(BaseTool):
    name = "get_file_outline"
    description = (
        "Get a token-efficient outline/skeleton of a file showing its structure: "
        "imports, class definitions, function signatures, and their line numbers. "
        "Use this BEFORE reading a large file to understand its structure and decide "
        "which specific sections to read with get_file_content. "
        "For small files (<=50 lines), returns the full content."
    )
    parameters = {
        "file_path": {
            "type": "string",
            "description": "Relative path of the file to outline.",
        },
    }
    required = ["file_path"]

    def execute(self, *, file_path: str, **_kw) -> str:
        abs_path, err = self.file_must_exist(file_path)
        if err:
            return err

        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            return f"Error reading {file_path}: {e}"

        total_lines = len(lines)
        file_size = os.path.getsize(abs_path)

        if file_size >= 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        elif file_size >= 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size} B"

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        header = f"File: {file_path} ({total_lines} lines, {size_str})\n"

        # Small files — just show entire content
        if total_lines <= 50:
            return header + "\n" + "".join(lines)

        imports, structures = self._parse(lines, ext)
        return self._format(header, imports, structures, lines, total_lines)

    # ------------------------------------------------------------------
    # Language-aware parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse(lines: list[str], ext: str) -> tuple[list[str], list[str]]:
        imports: list[str] = []
        structures: list[str] = []

        python = ext in (".py", ".pyw")
        js = ext in (".js", ".mjs", ".ts", ".tsx", ".jsx")
        c_family = ext in (".c", ".cpp", ".cc", ".h", ".hpp", ".cs", ".java", ".go", ".rs")
        html = ext in (".html", ".htm")

        for i, line in enumerate(lines, 1):
            stripped = line.rstrip()
            if not stripped or stripped.startswith("#!"):
                continue

            # --- Imports ---
            if python and stripped.startswith(("import ", "from ")):
                imports.append(f"  L{i}: {stripped}")
            elif js:
                if stripped.startswith("import "):
                    imports.append(f"  L{i}: {stripped}")
                elif stripped.startswith(("const ", "let ", "var ")) and "require(" in stripped:
                    imports.append(f"  L{i}: {stripped}")
            elif c_family:
                if stripped.startswith("#include"):
                    imports.append(f"  L{i}: {stripped}")
                elif stripped.startswith(("using ", "package ", "import ")):
                    imports.append(f"  L{i}: {stripped}")

            # --- Structures ---
            if python:
                m = re.match(r"^(class\s+\w+[^:]*:)", stripped)
                if m:
                    structures.append(f"  L{i}: {m.group(1)}")
                    continue
                m = re.match(r"^(\s*)(def\s+\w+\s*\([^)]*\)[^:]*:)", stripped)
                if m:
                    structures.append(f"  L{i}: {m.group(1)}{m.group(2)}")
                    continue
                if stripped.startswith("@"):
                    structures.append(f"  L{i}: {stripped}")
                    continue

            elif js:
                m = re.match(r"^((?:export\s+)?class\s+\w+[^{]*)", stripped)
                if m:
                    structures.append(f"  L{i}: {m.group(1)}")
                    continue
                m = re.match(r"^((?:export\s+)?(?:async\s+)?function\s+\w+\s*\([^)]*\))", stripped)
                if m:
                    structures.append(f"  L{i}: {m.group(1)}")
                    continue
                m = re.match(
                    r"^((?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\([^)]*\)\s*=>)",
                    stripped,
                )
                if m:
                    structures.append(f"  L{i}: {m.group(1)}")
                    continue

            elif c_family:
                m = re.match(
                    r"^(\s*(?:public|private|protected|static|virtual|override|async|fn|func)?"
                    r"\s*[\w<>\[\]*&]+\s+\w+\s*\([^)]*\))",
                    stripped,
                )
                if m and not stripped.startswith(("//", "/*", "*")):
                    structures.append(f"  L{i}: {m.group(1)}")
                    continue
                m = re.match(r"^((?:pub\s+)?(?:struct|class|enum|interface|trait)\s+\w+)", stripped)
                if m:
                    structures.append(f"  L{i}: {m.group(1)}")
                    continue

            elif html:
                if re.match(
                    r"^\s*<(html|head|body|script|style|div|section|main|nav|header|footer)",
                    stripped,
                    re.IGNORECASE,
                ):
                    structures.append(f"  L{i}: {stripped[:80]}")

        return imports, structures

    @staticmethod
    def _format(
        header: str,
        imports: list[str],
        structures: list[str],
        lines: list[str],
        total_lines: int,
    ) -> str:
        parts = [header]

        if imports:
            parts.append("Imports:")
            parts.extend(imports[:20])
            if len(imports) > 20:
                parts.append(f"  ... ({len(imports) - 20} more imports)")
            parts.append("")

        if structures:
            parts.append("Structure:")
            parts.extend(structures)
            parts.append("")

        if not imports and not structures:
            parts.append("Preview (first 10 lines):")
            for i, line in enumerate(lines[:10], 1):
                parts.append(f"  L{i}: {line.rstrip()}")
            parts.append(f"\n  ... ({total_lines - 15} lines omitted) ...\n")
            parts.append("Preview (last 5 lines):")
            for i, line in enumerate(lines[-5:], total_lines - 4):
                parts.append(f"  L{i}: {line.rstrip()}")

        return "\n".join(parts)
