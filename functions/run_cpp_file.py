import os
import subprocess
import json
from google.genai import types
from config import MAX_FILE_CHARS

def run_cpp_file(working_dir, path, args=None, compile_flags=None):
    """
    Compiles and runs a C++ file using g++.
    
    Args:
        working_dir: The working directory path
        path: Path to the C++ file (relative to working_dir)
        args: Optional list of command-line arguments to pass to the compiled program
        compile_flags: Optional list of compiler flags (e.g., ['-std=c++17', '-O2'])
    
    Returns:
        JSON string containing compilation output, execution output, and any errors
    """
    full_path = os.path.abspath(os.path.join(working_dir, path))
    working_dir_abs = os.path.abspath(working_dir)
    
    if not os.path.exists(full_path):
        return json.dumps({"error": f"File not found: {path}"})
    
    if not full_path.startswith(working_dir_abs + os.sep):
        return json.dumps({"error": "Security: Path traversal detected"})
    
    # Create output executable name
    output_name = os.path.splitext(path)[0]
    output_path = os.path.join(working_dir, output_name)
    
    # Build compilation command
    compile_cmd = ['g++', full_path, '-o', output_path]
    if compile_flags:
        compile_cmd.extend(compile_flags)
    
    result = {
        "file": path,
        "compilation": {},
        "execution": {}
    }
    
    # Step 1: Compile the C++ file
    try:
        compile_result = subprocess.run(
            compile_cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        result["compilation"]["stdout"] = compile_result.stdout[:MAX_FILE_CHARS]
        result["compilation"]["stderr"] = compile_result.stderr[:MAX_FILE_CHARS]
        result["compilation"]["return_code"] = compile_result.returncode
        
        # If compilation failed, return early
        if compile_result.returncode != 0:
            result["compilation"]["status"] = "failed"
            return json.dumps(result, indent=2)
        
        result["compilation"]["status"] = "success"
        
    except subprocess.TimeoutExpired:
        result["compilation"]["error"] = "Compilation timeout (30 seconds)"
        return json.dumps(result, indent=2)
    except Exception as e:
        result["compilation"]["error"] = str(e)
        return json.dumps(result, indent=2)
    
    # Step 2: Execute the compiled program
    try:
        exec_cmd = [output_path]
        if args:
            exec_cmd.extend(args)
        
        exec_result = subprocess.run(
            exec_cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        result["execution"]["stdout"] = exec_result.stdout[:MAX_FILE_CHARS]
        result["execution"]["stderr"] = exec_result.stderr[:MAX_FILE_CHARS]
        result["execution"]["return_code"] = exec_result.returncode
        result["execution"]["status"] = "completed"
        
    except subprocess.TimeoutExpired:
        result["execution"]["error"] = "Execution timeout (30 seconds)"
    except Exception as e:
        result["execution"]["error"] = str(e)
    finally:
        # Clean up the compiled executable
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except:
            pass
    
    return json.dumps(result, indent=2)


# Function schema for Gemini
schema_run_cpp_file = types.FunctionDeclaration(
    name="run_cpp_file",
    description="Compiles and executes a C++ file using g++. Returns compilation output and execution results.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "path": types.Schema(
                type=types.Type.STRING,
                description="Path to the C++ file relative to the working directory (e.g., 'main.cpp' or 'src/program.cpp')"
            ),
            "args": types.Schema(
                type=types.Type.ARRAY,
                description="Optional command-line arguments to pass to the compiled program",
                items=types.Schema(type=types.Type.STRING)
            ),
            "compile_flags": types.Schema(
                type=types.Type.ARRAY,
                description="Optional compiler flags (e.g., ['-std=c++17', '-O2', '-Wall'])",
                items=types.Schema(type=types.Type.STRING)
            )
        },
        required=["path"]
    )
)
