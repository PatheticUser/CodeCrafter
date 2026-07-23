import os
import sys
import subprocess
import webbrowser

from src.tools._security import validate_path


LANGUAGE_MAP = {
    ".py": {"run": ["python", "{file}"], "compile": None},
    ".js": {"run": ["node", "{file}"], "compile": None},
    ".mjs": {"run": ["node", "{file}"], "compile": None},
    ".ts": {"run": ["npx", "tsx", "{file}"], "compile": None},
    ".rb": {"run": ["ruby", "{file}"], "compile": None},
    ".go": {"run": ["go", "run", "{file}"], "compile": None},
    ".php": {"run": ["php", "{file}"], "compile": None},
    ".sh": {"run": ["bash", "{file}"], "compile": None},
    ".bat": {"run": ["cmd", "/c", "{file}"], "compile": None},
    ".ps1": {"run": ["powershell", "-File", "{file}"], "compile": None},
    ".cpp": {"compile": ["g++", "{file}", "-o", "{out}"], "run": ["{out}"]},
    ".cc": {"compile": ["g++", "{file}", "-o", "{out}"], "run": ["{out}"]},
    ".c": {"compile": ["gcc", "{file}", "-o", "{out}"], "run": ["{out}"]},
    ".rs": {"compile": ["rustc", "{file}", "-o", "{out}"], "run": ["{out}"]},
    ".java": {
        "compile": ["javac", "{file}"],
        "run": ["java", "-cp", "{dir}", "{class}"],
    },
    ".html": {"browser": True},
    ".htm": {"browser": True},
}

SUPPORTED_EXTENSIONS = ", ".join(sorted(LANGUAGE_MAP.keys()))


def run_code(working_directory, path, args=None, timeout=30):
    """
    Universal code runner. Auto-detects language from file extension.
    Compiles if needed, then executes. Cleans up compiled binaries.
    """
    err = validate_path(working_directory, path)
    if err:
        return err

    working_dir_abs = os.path.realpath(working_directory)
    full_path = os.path.realpath(os.path.join(working_directory, path))

    if not os.path.isfile(full_path):
        return f'Error: File not found: "{path}"'

    _, ext = os.path.splitext(path)
    ext = ext.lower()

    if ext not in LANGUAGE_MAP:
        return f'Error: Unsupported file type "{ext}". Supported: {SUPPORTED_EXTENSIONS}'

    lang = LANGUAGE_MAP[ext]

    if lang.get("browser"):
        try:
            file_url = f"file://{full_path}"
            webbrowser.open(file_url)
            return f"Opened {path} in the default browser"
        except Exception as e:
            return f"Error opening {path}: {e}"

    out_binary = None
    if lang.get("compile"):
        out_name = os.path.splitext(os.path.basename(path))[0]
        if sys.platform == "win32":
            out_name += ".exe"
        out_binary = os.path.join(working_dir_abs, out_name)

        compile_cmd = [
            c.replace("{file}", full_path).replace("{out}", out_binary)
            for c in lang["compile"]
        ]

        try:
            comp = subprocess.run(
                compile_cmd,
                cwd=working_dir_abs,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if comp.returncode != 0:
                error_msg = comp.stderr.strip() or comp.stdout.strip()
                return f"Compilation failed:\n{error_msg}"
        except subprocess.TimeoutExpired:
            return f"Error: Compilation timed out after {timeout}s"
        except FileNotFoundError as e:
            return f"Error: Compiler not found \u2014 {e}"
        except Exception as e:
            return f"Error during compilation: {e}"

    if ext == ".java":
        class_name = os.path.splitext(os.path.basename(path))[0]
        file_dir = os.path.dirname(full_path) or working_dir_abs
        run_cmd = [
            c.replace("{file}", full_path)
            .replace("{dir}", file_dir)
            .replace("{class}", class_name)
            for c in lang["run"]
        ]
    elif out_binary:
        run_cmd = [c.replace("{out}", out_binary) for c in lang["run"]]
    else:
        run_cmd = [c.replace("{file}", full_path) for c in lang["run"]]

    if args:
        run_cmd.extend(args)

    try:
        result = subprocess.run(
            run_cmd,
            cwd=working_dir_abs,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output_parts = []
        if result.stdout.strip():
            stdout = result.stdout.strip()
            if len(stdout) > 10000:
                stdout = stdout[:10000] + "\n...(output truncated)"
            output_parts.append(f"STDOUT:\n{stdout}")
        if result.stderr.strip():
            stderr = result.stderr.strip()
            if len(stderr) > 5000:
                stderr = stderr[:5000] + "\n...(stderr truncated)"
            output_parts.append(f"STDERR:\n{stderr}")

        if result.returncode != 0:
            output_parts.append(f"EXIT CODE: {result.returncode}")

        return (
            "\n".join(output_parts)
            if output_parts
            else "Code executed successfully (no output)."
        )

    except subprocess.TimeoutExpired:
        return f"Error: Execution timed out after {timeout}s"
    except FileNotFoundError as e:
        return f"Error: Runtime not found \u2014 {e}. Make sure the required runtime is installed."
    except Exception as e:
        return f"Error during execution: {e}"
    finally:
        if out_binary and os.path.exists(out_binary):
            try:
                os.remove(out_binary)
            except Exception:
                pass


schema_run_code = {
    "type": "function",
    "function": {
        "name": "run_code",
        "description": (
            "Execute a code file. Auto-detects language from file extension. "
            "Supports: Python (.py), JavaScript (.js/.mjs), TypeScript (.ts), "
            "C/C++ (.c/.cpp/.cc), Go (.go), Rust (.rs), Java (.java), "
            "Ruby (.rb), PHP (.php), Shell (.sh/.bat/.ps1). "
            "HTML files open in the browser. "
            "Compiles automatically for compiled languages. "
            "Returns stdout, stderr, and exit code."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
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
            },
            "required": ["path"],
        },
    },
}
