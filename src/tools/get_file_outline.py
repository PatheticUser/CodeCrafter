import os
import re


def get_file_outline(working_directory, file_path):
    """
    Returns a token-efficient skeleton of a file: imports, class definitions,
    function signatures with line numbers.
    """
    err = validate_path(working_directory, file_path)
    if err:
        return err

    target_file_abs = os.path.realpath(os.path.join(working_directory, file_path))

    if not os.path.isfile(target_file_abs):
        return f'Error: File not found: "{file_path}"'

    try:
        with open(target_file_abs, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        return f"Error reading {file_path}: {e}"

    total_lines = len(lines)
    file_size = os.path.getsize(target_file_abs)

    if file_size >= 1024 * 1024:
        size_str = f"{file_size / (1024 * 1024):.1f} MB"
    elif file_size >= 1024:
        size_str = f"{file_size / 1024:.1f} KB"
    else:
        size_str = f"{file_size} B"

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    header = f"File: {file_path} ({total_lines} lines, {size_str})\n"

    if total_lines <= 50:
        return header + "\n" + "".join(lines)

    imports = []
    structures = []

    python_patterns = ext in (".py", ".pyw")
    js_patterns = ext in (".js", ".mjs", ".ts", ".tsx", ".jsx")
    c_patterns = ext in (
        ".c", ".cpp", ".cc", ".h", ".hpp", ".cs", ".java", ".go", ".rs",
    )
    web_patterns = ext in (".html", ".htm", ".css", ".xml", ".svg")

    for i, line in enumerate(lines, 1):
        stripped = line.rstrip()

        if not stripped or stripped.startswith("#!"):
            continue

        if python_patterns:
            if stripped.startswith(("import ", "from ")):
                imports.append(f"  L{i}: {stripped}")
        elif js_patterns:
            if stripped.startswith(("import ", "const ")) and "require(" in stripped:
                imports.append(f"  L{i}: {stripped}")
            elif stripped.startswith("import "):
                imports.append(f"  L{i}: {stripped}")
        elif c_patterns:
            if stripped.startswith("#include"):
                imports.append(f"  L{i}: {stripped}")
            elif stripped.startswith(("using ", "package ", "import ")):
                imports.append(f"  L{i}: {stripped}")

        if python_patterns:
            m = re.match(r"^(class\s+\w+[^:]*:)", stripped)
            if m:
                structures.append(f"  L{i}: {m.group(1)}")
                continue
            m = re.match(r"^(\s*)(def\s+\w+\s*\([^)]*\)[^:]*:)", stripped)
            if m:
                indent = m.group(1)
                sig = m.group(2)
                structures.append(f"  L{i}: {indent}{sig}")
                continue
            if stripped.startswith("@"):
                structures.append(f"  L{i}: {stripped}")
                continue
        elif js_patterns:
            m = re.match(r"^((?:export\s+)?class\s+\w+[^{]*)", stripped)
            if m:
                structures.append(f"  L{i}: {m.group(1)}")
                continue
            m = re.match(
                r"^((?:export\s+)?(?:async\s+)?function\s+\w+\s*\([^)]*\))", stripped
            )
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
        elif c_patterns:
            m = re.match(
                r"^(\s*(?:public|private|protected|static|virtual|override|async|fn|func)?\s*[\w<>\[\]*&]+\s+\w+\s*\([^)]*\))",
                stripped,
            )
            if m and not stripped.startswith(("//", "/*", "*")):
                structures.append(f"  L{i}: {m.group(1)}")
                continue
            m = re.match(
                r"^((?:pub\s+)?(?:struct|class|enum|interface|trait)\s+\w+)", stripped
            )
            if m:
                structures.append(f"  L{i}: {m.group(1)}")
                continue
        elif web_patterns and ext in (".html", ".htm"):
            if re.match(
                r"^\s*<(html|head|body|script|style|div|section|main|nav|header|footer)",
                stripped,
                re.IGNORECASE,
            ):
                tag_preview = stripped[:80]
                structures.append(f"  L{i}: {tag_preview}")

    output_parts = [header]

    if imports:
        output_parts.append("Imports:")
        output_parts.extend(imports[:20])
        if len(imports) > 20:
            output_parts.append(f"  ... ({len(imports) - 20} more imports)")
        output_parts.append("")

    if structures:
        output_parts.append("Structure:")
        output_parts.extend(structures)
        output_parts.append("")

    if not imports and not structures:
        output_parts.append("Preview (first 10 lines):")
        for i, line in enumerate(lines[:10], 1):
            output_parts.append(f"  L{i}: {line.rstrip()}")
        output_parts.append(f"\n  ... ({total_lines - 15} lines omitted) ...\n")
        output_parts.append("Preview (last 5 lines):")
        for i, line in enumerate(lines[-5:], total_lines - 4):
            output_parts.append(f"  L{i}: {line.rstrip()}")

    return "\n".join(output_parts)


schema_get_file_outline = {
    "type": "function",
    "function": {
        "name": "get_file_outline",
        "description": (
            "Get a token-efficient outline/skeleton of a file showing its structure: "
            "imports, class definitions, function signatures, and their line numbers. "
            "Use this BEFORE reading a large file to understand its structure and decide "
            "which specific sections to read with get_file_content. "
            "For small files (<=50 lines), returns the full content."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The relative path of the file to outline.",
                },
            },
            "required": ["file_path"],
        },
    },
}
