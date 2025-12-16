import os
import sys
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from config import WORKING_DIR, PROJECT_DESCRIPTION_FILE, AUTO_UPDATE_DESCRIPTION
from functions.get_files_info import get_files_info, schema_get_files_info
from functions.get_file_content import get_file_content, schema_get_file_content
from functions.write_file import write_file, schema_write_file
from functions.run_python_file import run_python_file, schema_run_python_file
from functions.run_cpp_file import run_cpp_file, schema_run_cpp_file
from functions.run_js_file import run_js_file, schema_run_js_file
from functions.preview_html_file import preview_html_file, schema_preview_html_file
from functions.delete_file import delete_file, schema_delete_file
from functions.get_project_description import (
    get_project_description,
    schema_get_project_description,
)
from functions.update_project_description import scan_and_rebuild_description
from functions.set_project_context import (
    set_project_context,
    schema_set_project_context,
)

VERSION = "1.5.0"

class Icons:
    AGENT = ""
    CODE = ""
    FILE = ""
    FOLDER = ""
    SUCCESS = ""
    ERROR = ""
    WARNING = ""
    INFO = ""
    PROMPT = "󰶻"
    ARROW = ""
    GEAR = ""
    PLAY = ""
    STOP = ""
    TOKENS = ""
    TIME = "󰚭"
    SEARCH = ""
    WRITE = ""
    DELETE = ""
    DEBUG = ""


class Colors:
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def c(text: str, color: str) -> str:
    return f"{color}{text}{Colors.RESET}"

def dim(text: str) -> str:
    return c(text, Colors.DIM)

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


# INTRO BANNER
def show_intro_banner(user_name: str):
    clear_screen()
    print()
    print(f"  {c(Icons.AGENT, Colors.CYAN)}  {c('CodeCrafter', Colors.BOLD)}  {dim('v' + VERSION)}")
    print(f"  {dim('─' * 52)}")
    print(f"  {dim(Icons.GEAR)}  Model: {c('gemini-2.5-flash', Colors.CYAN)}  {dim('│')}  Mode: {c('Interactive', Colors.GREEN)}")
    print(f"  {dim(Icons.INFO)}  Type {c('exit', Colors.YELLOW)} or {c('quit', Colors.YELLOW)} to close")
    print()
    print(f"  {c(Icons.SUCCESS, Colors.GREEN)}  Hello {c(user_name, Colors.MAGENTA)}, ready to build something solid")
    print()


# EXIT BANNER
def show_exit_banner(user_name: str):
    print()
    print(f"  {dim('─' * 52)}")
    print(f"  {c(Icons.STOP, Colors.RED)}  {c('Session Ended', Colors.BOLD)}")
    print(f"  {dim(Icons.INFO)}  Context cleared, See you soon, {c(user_name, Colors.MAGENTA)}")
    print()


# VERBOSE CONFIG
def show_verbose_config(working_dir: str, auto_update: bool):
    print()
    print(f"  {c(Icons.DEBUG, Colors.YELLOW)}  {c('Verbose Mode', Colors.BOLD)}")
    print(f"  {dim('  ├─')}  Working Dir: {c(working_dir, Colors.CYAN)}")
    print(f"  {dim('  └─')}  Auto-update: {c(str(auto_update), Colors.GREEN if auto_update else Colors.RED)}")


# VERBOSE STEP
def show_verbose_step(step: int):
    print()
    print(f"  {c(Icons.PLAY, Colors.CYAN)}  {c(f'Step {step}', Colors.BOLD)}  {dim('processing...')}")


# VERBOSE FUNCTION
def show_verbose_function(func_name: str, func_args: dict):
    args_display = str(func_args)
    if len(args_display) > 60:
        args_display = args_display[:60] + "..."
    print(f"  {dim('  ├─')}  {Icons.CODE}  {c(func_name, Colors.MAGENTA)}({dim(args_display)})")


# VERBOSE RESULT
def show_verbose_result(result: str, is_error: bool = False):
    icon = Icons.ERROR if is_error else Icons.SUCCESS
    color = Colors.RED if is_error else Colors.GREEN

    truncated = result[:150] + "..." if len(result) > 150 else result
    lines = truncated.split("\n")
    if len(lines) > 3:
        truncated = "\n".join(lines[:3]) + "\n..."

    print(f"  {dim('  └─')}  {c(icon, color)}  {dim(truncated.replace(chr(10), ' '))}")


# TOKEN DISPLAY
def show_verbose_tokens(prompt: int, response: int):
    total = prompt + response
    print(f"     {c(Icons.TOKENS, Colors.DIM)}  {dim(f'tokens: {prompt:,} in │ {response:,} out │ {total:,} total')}")


# FUNCTION CALL INDICATOR
def show_function_call(func_name: str, target: str):
    icon_map = {
        "get_files_info": Icons.FOLDER,
        "get_file_content": Icons.FILE,
        "write_file": Icons.WRITE,
        "delete_file": Icons.DELETE,
        "run_python_file": Icons.PLAY,
        "run_cpp_file": Icons.PLAY,
        "run_js_file": Icons.PLAY,
        "preview_html_file": Icons.SEARCH,
        "get_project_description": Icons.INFO,
        "set_project_context": Icons.GEAR,
    }

    icon = icon_map.get(func_name, Icons.CODE)
    print(f"  {c(icon, Colors.DIM)}  {c(Icons.ARROW, Colors.CYAN)}  {func_name}  {dim(f'({target})')}")


# AGENT RESPONSE
def show_agent_response(response_text: str):
    print()
    print(f"  {c(Icons.AGENT, Colors.CYAN)}  {c('CodeCrafter', Colors.BOLD)}")
    print(f"  {dim('─' * 52)}")
    for line in response_text.split("\n"):
        print(f"  {line}")
    print()


# WARNINGS
def show_warning(message: str):
    print()
    print(f"  {c(Icons.WARNING, Colors.YELLOW)}  {c('Warning', Colors.BOLD)}: {message}")


# ERRORS
def show_error(message: str):
    print(f"  {c(Icons.ERROR, Colors.RED)}  {message}")


# PROMPT FOR NAME
def get_user_name() -> str:
    clear_screen()
    print()
    print(f"  {c(Icons.AGENT, Colors.CYAN)}  {c('CodeCrafter', Colors.BOLD)}")
    print(f"  {dim('─' * 52)}")
    print(f"  {dim(Icons.INFO)}  Project-aware AI coding assistant")
    print()
    user_name = input(f"  {Icons.PROMPT}  Your name {c('›', Colors.CYAN)} ").strip()
    if not user_name:
        user_name = "Developer"
    return user_name
# --- Configuration & Initialization ---

# Load environment variables
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

try:
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable not found. Please set it in your .env file."
        )
    client = genai.Client(api_key=api_key)
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    sys.exit(1)

# Parse CLI flags
args = sys.argv[1:]
verbose_mode = "--verbose" in args
rebuild_description = "--rebuild-description" in args

# Get user's name for personalized experience
USER_NAME = get_user_name()

# Show intro banner
show_intro_banner(USER_NAME)

if verbose_mode:
    show_verbose_config(WORKING_DIR, AUTO_UPDATE_DESCRIPTION)

# If --rebuild-description flag is set, rebuild the project description
if rebuild_description:
    print("Rebuilding project_description.json...")
    result = scan_and_rebuild_description(WORKING_DIR)
    print(result)
    print("You can now run the agent normally.")

# Load project metadata once at startup
try:
    with open(
        os.path.join(WORKING_DIR, PROJECT_DESCRIPTION_FILE), "r", encoding="utf-8"
    ) as f:
        PROJECT_METADATA = json.load(f)
except FileNotFoundError:
    print(
        f"Error: {PROJECT_DESCRIPTION_FILE} not found in {WORKING_DIR}. Creating initial version..."
    )
    scan_and_rebuild_description(WORKING_DIR)
    try:
        with open(
            os.path.join(WORKING_DIR, PROJECT_DESCRIPTION_FILE), "r", encoding="utf-8"
        ) as f:
            PROJECT_METADATA = json.load(f)
    except:
        PROJECT_METADATA = {"key_files": {}}
except Exception as e:
    print(f"Error loading {PROJECT_DESCRIPTION_FILE}: {e}")
    PROJECT_METADATA = {"key_files": {}}

# Define the content to inject into the start of the conversation
# Using a system role for project metadata is often better than a user role for context injection
PROJECT_SUMMARY_MESSAGE = types.Content(
    role="user",  # Changed to 'system' to align with modern best practices for context
    parts=[
        types.Part(text=f"Project Metadata: {json.dumps(PROJECT_METADATA, indent=2)}")
    ],
)

# Agent Name for clear terminal output
AGENT_NAME = "CodeCrafter"


# System prompt (The instruction set for the model) - Kept largely the same
system_prompt = """
You are an expert AI assistant operating in a closed, local coding environment. Your singular goal is to efficiently and reliably complete the user's software development and file-related requests.

**Adaptive Workspace Management**

You MUST organize files intelligently based on the user's request:

1. **Project Requests** (e.g., "create a calculator app", "build a todo list", "make a game"):
   - Create a dedicated folder with a descriptive name (e.g., "calculator/", "todo_app/", "snake_game/")
   - Place ALL project files inside that folder
   - Update project_description.json to reflect the new project context

2. **Simple File Requests** (e.g., "write a script to...", "create a function that...", "make a file for..."):
   - Create files directly in the workspace root
   - Keep them as standalone files without a project folder

3. **When working on existing projects**:
   - Check project_description.json to understand the current project context
   - Continue working within the existing project folder structure

**Core Protocol: Project-Aware CoT**

You must adhere to a strict Chain of Thought (CoT) workflow to ensure strategic execution:

1. First, check the **project_description.json** to understand the current workspace state and any active project.
2. Determine if the user's request is a new project, continuation of existing project, or simple file task.
3. Generate a clear, step-by-step **Function Call Plan** specifying exact file paths.
4. Execute and present results, summarizing the outcome.

Self-Correction: If a function's output contradicts your plan, immediately update your plan before proceeding.

**Available Tools**

Your operations are strictly limited to the following file system and execution primitives (all paths must be RELATIVE to the working directory):
- **get_files_info**: Lists contents of a directory. Use primarily for quick confirmation of existence.
- **get_file_content**: Fetches the code or data required for analysis or modification.
- **write_file**: Creates or overwrites code, configuration, or data files. (The primary action tool).
- **delete_file**: Safely removes a file from the working directory. Use with extreme caution.
- **run_python_file**: Runs a Python script to test, compile, or run logic.
- **run_cpp_file**: Compiles and executes C++ code using g++.
- **run_js_file**: Executes JavaScript files using Node.js or Bun runtime.
- **preview_html_file**: Opens an HTML file in the default web browser for preview.
- **get_project_description**: Fetches the project metadata.

**Guiding Constraints**

* **Workspace Awareness**: ALWAYS check and update project_description.json to maintain accurate workspace state. When creating a new project, update the project_name field appropriately.
* **Token Efficiency**: Leverage file descriptions to select minimal files to read.
* **Code Integrity**: Validate changes using run_python_file on test files when available.
* **Security & Environment**: All file operations are restricted to the WORKING_DIR.
* **Response Style**: Do not use bold, italic or any other markdown in your responses.
"""

# Combine all function schemas into the Tool definition
available_functions = types.Tool(
    function_declarations=[
        schema_get_files_info,
        schema_get_file_content,
        schema_write_file,
        schema_run_python_file,
        schema_run_cpp_file,
        schema_run_js_file,
        schema_preview_html_file,
        schema_delete_file,
        schema_get_project_description,
        schema_set_project_context,
    ]
)

# Initialize chat history OUTSIDE the loop to maintain context
messages = []

# --- Main Agent Loop ---


while True:
    user_prompt = input(f"\n  {c(Icons.PROMPT, Colors.MAGENTA)} {c(USER_NAME, Colors.BOLD)} {c('›', Colors.CYAN)} ")
    if user_prompt.lower() in ["e", "q", "exit", "quit"]:
        show_exit_banner(USER_NAME)
        break

    # Improvement: Append the new user message to the existing history
    messages.append(types.Content(role="user", parts=[types.Part(text=user_prompt)]))

    # --- Inject Project Metadata on the FIRST turn only ---
    if len(messages) == 1:
        # Insert the PROJECT_SUMMARY_MESSAGE as a system message at the start (index 0)
        messages.insert(0, PROJECT_SUMMARY_MESSAGE)
        if verbose_mode:
            print(f"  {dim('   ')} {c(Icons.INFO, Colors.DIM)} {dim('injected project metadata')}")

    # --- Agentic Loop (max 20 steps) ---
    for step in range(20):
        if verbose_mode:
            show_verbose_step(step + 1)

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=messages,
                config=types.GenerateContentConfig(
                    tools=[available_functions], system_instruction=system_prompt
                ),
            )
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print()
                print(f"  {c(Icons.WARNING, Colors.YELLOW)}  {c('API Limit Reached', Colors.BOLD)}")
                print(f"  {dim('─' * 52)}")
                print(f"  {dim(Icons.INFO)}  You've hit your Gemini API quota for now.")
                print(f"  {dim(Icons.TIME)}  Wait a minute and try again, or check your")
                print(f"       Google AI Studio billing/plan settings.")
                print()
            elif "400" in error_str or "INVALID_ARGUMENT" in error_str:
                print()
                print(f"  {c(Icons.ERROR, Colors.RED)}  {c('Request Error', Colors.BOLD)}")
                print(f"  {dim('─' * 52)}")
                print(f"  {dim(Icons.INFO)}  The request was too large or malformed.")
                print(f"       Try a simpler query or start fresh.")
                print()
            elif "503" in error_str or "UNAVAILABLE" in error_str:
                print()
                print(f"  {c(Icons.WARNING, Colors.YELLOW)}  {c('Service Temporarily Unavailable', Colors.BOLD)}")
                print(f"  {dim('─' * 52)}")
                print(f"  {dim(Icons.INFO)}  Gemini API is experiencing high load.")
                print(f"  {dim(Icons.TIME)}  Please wait a moment and try again.")
                print()
            else:
                show_error(f"Model error: {e}")
            messages.pop()
            if (
                len(messages) > 0 and messages[0].role == "system"
            ):
                messages.pop(0)
            break

        # 1. Add model's reasoning/thoughts (content) to history
        if response.candidates and response.candidates[0].content:
            messages.append(response.candidates[0].content)

        # 2. Handle tool calls
        if response.function_calls:
            for fc in response.function_calls:
                func_name = fc.name
                func_args = dict(fc.args)

                # Get path/file_path for display purposes
                file_path = func_args.get("file_path") or func_args.get("path")
                project_name = func_args.get("project_name")

                # --- Clean UI for Function Call (Non-Verbose Mode) ---
                if func_name == "write_file":
                    display_args = f"file_path='{file_path}', content='...' (writing {len(func_args.get('content', ''))} chars)"
                elif func_name in ["run_python_file", "run_cpp_file", "run_js_file", "preview_html_file"]:
                    display_args = f"path='{file_path}'"
                elif func_name == "set_project_context":
                    display_args = f"project='{project_name}'"
                elif file_path:
                    display_args = f"file_path='{file_path}'"
                else:
                    display_args = ", ".join(f"{k}='{v}'" for k, v in func_args.items())

                # Show a glance of the action for the end user
                show_function_call(func_name, project_name or file_path or 'context')

                # Show full arguments only in verbose mode
                if verbose_mode:
                    show_verbose_function(func_name, func_args)

                try:
                    # Function execution logic
                    if func_name == "get_files_info":
                        result = get_files_info(WORKING_DIR, **func_args)
                    elif func_name == "get_file_content":
                        result = get_file_content(WORKING_DIR, **func_args)
                    elif func_name == "write_file":
                        result = write_file(WORKING_DIR, **func_args)
                    elif func_name == "run_python_file":
                        result = run_python_file(WORKING_DIR, **func_args)
                    elif func_name == "run_cpp_file":
                        result = run_cpp_file(WORKING_DIR, **func_args)
                    elif func_name == "run_js_file":
                        result = run_js_file(WORKING_DIR, **func_args)
                    elif func_name == "preview_html_file":
                        result = preview_html_file(WORKING_DIR, **func_args)
                    elif func_name == "delete_file":
                        result = delete_file(WORKING_DIR, **func_args)
                    elif func_name == "get_project_description":
                        result = get_project_description(WORKING_DIR, **func_args)
                    elif func_name == "set_project_context":
                        result = set_project_context(WORKING_DIR, **func_args)
                    else:
                        result = f"Error: Unknown function {func_name}"
                except Exception as e:
                    # Capture execution errors clearly for the model and user
                    result = f"ERROR executing {func_name}: {e}"

                # Print result to the user only in verbose mode
                if verbose_mode:
                    is_error = "ERROR" in str(result) or "Error" in str(result)
                    show_verbose_result(str(result), is_error)

                # 3. Feedback to agent (so it knows tool outcome) - ALWAYS send the result to the model
                messages.append(
                    types.Content(
                        role="user",
                        parts=[types.Part(text=f"Function call result: {result}")],
                    )
                )

        # 4. If final text output exists, finish loop
        elif response.text:
            show_agent_response(response.text)
            break

        # 5. Check for max steps
        if step == 19:
            show_warning(f"{AGENT_NAME} reached max steps ({step + 1}). Resetting...")
            messages = []
            break

        # 6. Usage info each iteration if in verbose mode
        if verbose_mode and hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            show_verbose_tokens(usage.prompt_token_count, usage.candidates_token_count)
