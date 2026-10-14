"""Tool: run_code — multi-language code runner executing inside workspace."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from src.workspace.base import CommandResult, Workspace
from src.workspace.local import LocalWorkspace

LANGUAGE_MAP = {
    ".py": {"run": "python {file}", "compile": None},
    ".js": {"run": "node {file}", "compile": None},
    ".mjs": {"run": "node {file}", "compile": None},
    ".ts": {"run": "npx tsx {file}", "compile": None},
    ".rb": {"run": "ruby {file}", "compile": None},
    ".go": {"run": "go run {file}", "compile": None},
    ".php": {"run": "php {file}", "compile": None},
    ".sh": {"run": "bash {file}", "compile": None},
    ".cpp": {"compile": "g++ {file} -o {out}", "run": "{out}"},
    ".cc": {"compile": "g++ {file} -o {out}", "run": "{out}"},
    ".c": {"compile": "gcc {file} -o {out}", "run": "{out}"},
    ".rs": {"compile": "rustc {file} -o {out}", "run": "{out}"},
    ".java": {"compile": "javac {file}", "run": "java -cp {dir} {class}"},
    ".html": {"browser": True},
    ".htm": {"browser": True},
}

SUPPORTED_EXTENSIONS = ", ".join(sorted(LANGUAGE_MAP.keys()))


async def run_code(
    workspace: Workspace | Path | str,
    path: str,
    args: list[str] | None = None,
    timeout: int = 30,
) -> str:
    """Universal code runner executing inside the sandboxed workspace."""
    if isinstance(workspace, (str, Path)):
        ws: Workspace = LocalWorkspace(workspace_id="local", root_dir=workspace)
    else:
        ws = workspace

    _, ext = os.path.splitext(path)
    ext = ext.lower()

    if ext not in LANGUAGE_MAP:
        return f'Error: Unsupported file type "{ext}". Supported: {SUPPORTED_EXTENSIONS}'

    lang = LANGUAGE_MAP[ext]

    if lang.get("browser"):
        return f"HTML file ready for inspection in workspace: '{path}'"

    clean_path = path.lstrip("/\\")
    out_binary_name = None

    if lang.get("compile"):
        base_name = os.path.splitext(os.path.basename(clean_path))[0]
        out_binary_name = f"./{base_name}.out" if sys.platform != "win32" else f"./{base_name}.exe"
        compile_cmd = lang["compile"].format(file=clean_path, out=out_binary_name)
        comp_res: CommandResult = await ws.execute_command(compile_cmd, timeout=timeout)
        if comp_res.exit_code != 0:
            err = comp_res.stderr.strip() or comp_res.stdout.strip()
            return f"Compilation failed:\n{err}"

    if ext == ".java":
        class_name = os.path.splitext(os.path.basename(clean_path))[0]
        file_dir = os.path.dirname(clean_path) or "."
        run_cmd_str = lang["run"].format(dir=file_dir, class_name=class_name)
    elif out_binary_name:
        run_cmd_str = lang["run"].format(out=out_binary_name)
    else:
        run_cmd_str = lang["run"].format(file=clean_path)

    if args:
        run_cmd_str += " " + " ".join(args)

    try:
        run_res: CommandResult = await ws.execute_command(run_cmd_str, timeout=timeout)
        return run_res.to_formatted_output()
    finally:
        if out_binary_name:
            try:
                await ws.delete_file(out_binary_name.removeprefix("./"))
            except Exception:
                pass


schema_run_code = {
    "type": "function",
    "function": {
        "name": "run_code",
        "description": (
            "Execute a code file. Auto-detects language: "
            ".py .js .ts .c .cpp .go .rs .java .rb .php .sh .html."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to workspace.",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CLI arguments for the program.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max seconds. Default 30.",
                },
            },
            "required": ["path"],
        },
    },
}
