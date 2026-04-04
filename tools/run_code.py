"""Tool: run_code — universal code runner with auto-compilation."""

import os
import sys
import subprocess
import webbrowser

from tools.base import BaseTool

# Language configuration: extension -> (compile_cmd, run_cmd)
LANGUAGE_MAP = {
    # Interpreted
    ".py":  {"run": ["python", "{file}"], "compile": None},
    ".js":  {"run": ["node", "{file}"], "compile": None},
    ".mjs": {"run": ["node", "{file}"], "compile": None},
    ".ts":  {"run": ["npx", "tsx", "{file}"], "compile": None},
    ".rb":  {"run": ["ruby", "{file}"], "compile": None},
    ".go":  {"run": ["go", "run", "{file}"], "compile": None},
    ".php": {"run": ["php", "{file}"], "compile": None},
    ".sh":  {"run": ["bash", "{file}"], "compile": None},
    ".bat": {"run": ["cmd", "/c", "{file}"], "compile": None},
    ".ps1": {"run": ["powershell", "-File", "{file}"], "compile": None},
    # Compiled
    ".cpp": {"compile": ["g++", "{file}", "-o", "{out}"], "run": ["{out}"]},
    ".cc":  {"compile": ["g++", "{file}", "-o", "{out}"], "run": ["{out}"]},
    ".c":   {"compile": ["gcc", "{file}", "-o", "{out}"], "run": ["{out}"]},
    ".rs":  {"compile": ["rustc", "{file}", "-o", "{out}"], "run": ["{out}"]},
    ".java": {
        "compile": ["javac", "{file}"],
        "run": ["java", "-cp", "{dir}", "{class}"],
    },
    # Browser
    ".html": {"browser": True},
    ".htm":  {"browser": True},
}

SUPPORTED_EXTENSIONS = ", ".join(sorted(LANGUAGE_MAP.keys()))


class RunCodeTool(BaseTool):
    name = "run_code"
    description = (
        "Execute a code file. Auto-detects language from file extension. "
        "Supports: Python (.py), JavaScript (.js/.mjs), TypeScript (.ts), "
        "C/C++ (.c/.cpp/.cc), Go (.go), Rust (.rs), Java (.java), "
        "Ruby (.rb), PHP (.php), Shell (.sh/.bat/.ps1). "
        "HTML files open in the browser. "
        "Compiles automatically for compiled languages. "
        "Returns stdout, stderr, and exit code."
    )
    parameters = {
        "file_path": {
            "type": "string",
            "description": "Path to the file to execute, relative to the working directory.",
        },
        "args": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional command-line arguments to pass to the program.",
        },
        "timeout": {
            "type": "integer",
            "description": "Maximum seconds to wait for execution. Default is 30.",
        },
    }
    required = ["file_path"]
    auto_fixable = True

    def execute(self, *, file_path: str, args: list[str] | None = None, timeout: int = 30, **_kw) -> str:
        abs_path, err = self.file_must_exist(file_path)
        if err:
            return err

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext not in LANGUAGE_MAP:
            return f'Error: Unsupported file type "{ext}". Supported: {SUPPORTED_EXTENSIONS}'

        lang = LANGUAGE_MAP[ext]

        # Browser-based files
        if lang.get("browser"):
            try:
                webbrowser.open(f"file://{abs_path}")
                return f"Opened {file_path} in the default browser"
            except Exception as e:
                return f"Error opening {file_path}: {e}"

        # Compiled languages
        out_binary = None
        if lang.get("compile"):
            out_binary, compile_err = self._compile(abs_path, file_path, lang, timeout)
            if compile_err:
                return compile_err

        # Build run command
        run_cmd = self._build_run_cmd(abs_path, file_path, ext, lang, out_binary)
        if args:
            run_cmd.extend(args)

        # Execute
        try:
            return self._run(run_cmd, timeout)
        finally:
            if out_binary and os.path.exists(out_binary):
                try:
                    os.remove(out_binary)
                except OSError:
                    pass

    def _compile(self, abs_path: str, file_path: str, lang: dict, timeout: int) -> tuple[str, str | None]:
        """Compile the source file. Returns (out_binary_path, error_or_None)."""
        out_name = os.path.splitext(os.path.basename(file_path))[0]
        if sys.platform == "win32":
            out_name += ".exe"
        out_binary = os.path.join(self.working_directory, out_name)

        compile_cmd = [
            c.replace("{file}", abs_path).replace("{out}", out_binary)
            for c in lang["compile"]
        ]

        try:
            comp = subprocess.run(
                compile_cmd, cwd=self.working_directory,
                capture_output=True, text=True, timeout=timeout,
            )
            if comp.returncode != 0:
                error_msg = comp.stderr.strip() or comp.stdout.strip()
                return "", f"Compilation failed:\n{error_msg}"
        except subprocess.TimeoutExpired:
            return "", f"Error: Compilation timed out after {timeout}s"
        except FileNotFoundError as e:
            return "", f"Error: Compiler not found — {e}"
        except Exception as e:
            return "", f"Error during compilation: {e}"

        return out_binary, None

    def _build_run_cmd(self, abs_path: str, file_path: str, ext: str, lang: dict, out_binary: str | None) -> list[str]:
        if ext == ".java":
            class_name = os.path.splitext(os.path.basename(file_path))[0]
            file_dir = os.path.dirname(abs_path) or self.working_directory
            return [
                c.replace("{file}", abs_path).replace("{dir}", file_dir).replace("{class}", class_name)
                for c in lang["run"]
            ]
        elif out_binary:
            return [c.replace("{out}", out_binary) for c in lang["run"]]
        else:
            return [c.replace("{file}", abs_path) for c in lang["run"]]

    def _run(self, run_cmd: list[str], timeout: int) -> str:
        try:
            result = subprocess.run(
                run_cmd, cwd=self.working_directory,
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return f"Error: Execution timed out after {timeout}s"
        except FileNotFoundError as e:
            return f"Error: Runtime not found — {e}. Make sure the required runtime is installed."
        except Exception as e:
            return f"Error during execution: {e}"

        parts: list[str] = []
        if result.stdout.strip():
            stdout = result.stdout.strip()
            if len(stdout) > 10000:
                stdout = stdout[:10000] + "\n...(output truncated)"
            parts.append(f"STDOUT:\n{stdout}")
        if result.stderr.strip():
            stderr = result.stderr.strip()
            if len(stderr) > 5000:
                stderr = stderr[:5000] + "\n...(stderr truncated)"
            parts.append(f"STDERR:\n{stderr}")
        if result.returncode != 0:
            parts.append(f"EXIT CODE: {result.returncode}")

        return "\n".join(parts) if parts else "Code executed successfully (no output)."
