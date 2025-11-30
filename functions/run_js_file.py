import os
import subprocess
import json
from google.genai import types
from config import MAX_FILE_CHARS

def run_js_file(working_dir, path, args=None, runtime="node"):
    """
    Executes a JavaScript file using Node.js or Bun.
    
    Args:
        working_dir: The working directory path
        path: Path to the JavaScript file (relative to working_dir)
        args: Optional list of command-line arguments
        runtime: JavaScript runtime to use ('node' or 'bun', defaults to 'node')
    
    Returns:
        JSON string containing execution output, errors, and return code
    """
    full_path = os.path.abspath(os.path.join(working_dir, path))
    working_dir_abs = os.path.abspath(working_dir)
    
    if not os.path.exists(full_path):
        return json.dumps({"error": f"File not found: {path}"})
    
    if not full_path.startswith(working_dir_abs + os.sep):
        return json.dumps({"error": "Security: Path traversal detected"})
    
    # Validate runtime
    if runtime not in ["node", "bun"]:
        runtime = "node"
    
    # Build execution command
    cmd = [runtime, full_path]
    if args:
        cmd.extend(args)
    
    result = {
        "file": path,
        "runtime": runtime,
        "stdout": "",
        "stderr": "",
        "return_code": None
    }
    
    try:
        proc = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        result["stdout"] = proc.stdout[:MAX_FILE_CHARS]
        result["stderr"] = proc.stderr[:MAX_FILE_CHARS]
        result["return_code"] = proc.returncode
        
    except subprocess.TimeoutExpired:
        result["error"] = "Execution timeout (30 seconds)"
    except FileNotFoundError:
        result["error"] = f"Runtime '{runtime}' not found. Please ensure it is installed."
    except Exception as e:
        result["error"] = str(e)
    
    return json.dumps(result, indent=2)


# Function schema for Gemini
schema_run_js_file = types.FunctionDeclaration(
    name="run_js_file",
    description="Executes a JavaScript file using Node.js or Bun runtime. Returns stdout, stderr, and exit code.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "path": types.Schema(
                type=types.Type.STRING,
                description="Path to the JavaScript file relative to the working directory (e.g., 'index.js' or 'src/app.js')"
            ),
            "args": types.Schema(
                type=types.Type.ARRAY,
                description="Optional command-line arguments to pass to the script",
                items=types.Schema(type=types.Type.STRING)
            ),
            "runtime": types.Schema(
                type=types.Type.STRING,
                description="JavaScript runtime to use: 'node' (default) or 'bun'"
            )
        },
        required=["path"]
    )
)
