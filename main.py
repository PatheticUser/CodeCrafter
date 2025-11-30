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

VERSION = "1.3.0"

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def show_intro_banner(user_name: str):
    clear_screen()
    print()
    print("  ╭──────────────────────────────────────────────────────────────╮")
    print(f"  │   CodeCrafter Agent v{VERSION}  •  Project-Aware Assistant   │")
    print("  ├──────────────────────────────────────────────────────────────┤")
    print("  │   Model: gemini-2.5-flash   │   Mode: Interactive CLI      │")
    print("  │   Type 'exit' or 'quit' anytime to close                    │")
    print("  ╰──────────────────────────────────────────────────────────────╯")
    print()
    print(f"  Hello {user_name}, CodeCrafter is online — synced and ready <3")
    print()

def show_exit_banner(user_name: str):
    print()
    print("  ╭──────────────────────────────────────────────────────────────╮")
    print("  │              Shutting down CodeCrafter Agent...              │")
    print("  ├──────────────────────────────────────────────────────────────┤")
    print("  │   Session ended. All context cleared.                        │")
    print(f"  │   See you soon, {user_name} — keep building smart.".ljust(64) + "│")
    print("  ╰──────────────────────────────────────────────────────────────╯")
    print()

def show_verbose_header(step: int, action: str = "Calling model"):
    print()
    print(f"  ┌─ Step {step} ─────────────────────────────────────────────────┐")
    print(f"  │  {action}...")
    print("  └───────────────────────────────────────────────────────────────┘")

def show_verbose_info(label: str, value: str):
    print(f"  ├─ {label}: {value}")

def show_verbose_result(result: str):
    truncated = result[:200] + "..." if len(result) > 200 else result
    print(f"  └─ Result: {truncated}")

def get_user_name() -> str:
    print()
    print("  ╭──────────────────────────────────────────────────────────────╮")
    print("  │              Welcome to CodeCrafter Agent!                   │")
    print("  ╰──────────────────────────────────────────────────────────────╯")
    print()
    user_name = input("  What's your name? → ").strip()
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
    print("  ┌─ Verbose Mode ──────────────────────────────────────────────┐")
    print(f"  │  Working Directory: {WORKING_DIR}")
    print(f"  │  Auto-update Description: {AUTO_UPDATE_DESCRIPTION}")
    print("  └───────────────────────────────────────────────────────────────┘")

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

**Core Protocol: Project-Aware CoT**

You must adhere to a strict Chain of Thought (CoT) workflow to ensure strategic execution. Your protocol is now informed by the project's metadata:

1. First, check for and read the **project_description.json** file. Use the **project_summary**, file descriptions, and **debug_notes** to understand the project's architecture and the goal of the user's request.
2. Based on the user's request and the project metadata, generate a clear, step-by-step **Function Call Plan**. This plan should specify the exact file(s) that need reading or modifying.
3. Perform the next single function call from your plan.
4. Present the results. If the task is complete, summarize the final outcome and confirm that testing (if applicable) was successful. If the task is ongoing, present the updated plan and ask for confirmation to proceed.

Self-Correction: If a function's output (like a traceback from `run_python_file` or unexpected file content) contradicts your plan or the project metadata, immediately update your plan before proceeding.

**Available Tools**

Your operations are strictly limited to the following file system and execution primitives (all paths must be RELATIVE to the working directory):
- **get_files_info**: Lists contents of a directory. Use primarily for quick confirmation of existence, not for discovering files (use metadata for that).
- **get_file_content**: Fetches the code or data required for detailed analysis or modification.
- **write_file**: Creates or overwrites code, configuration, or data files. (The primary action tool).
- **delete_file**: Safely removes a file from the working directory. Use with extreme caution and only when explicitly required by the user or your plan.
- **run_python_file**: Runs a Python script to test, compile, or run logic, returning the stdout and stderr output.
- **run_cpp_file**: Compiles and executes C++ code using g++, returning compilation and execution results.
- **run_js_file**: Executes JavaScript files using Node.js or Bun runtime, returning stdout and stderr.
- **preview_html_file**: Opens an HTML file (with CSS support) in the default web browser for preview.
- **get_project_description**: Fetches the project metadata.

**Guiding Constraints**

* **Token Efficiency**: Leverage the file descriptions in "project_description.json" to understand the project structure and select the minimal set of files to read. Only use `get_file_content` on files specifically identified as relevant and necessary.
* **Code Integrity**: For bug fixes or new features, your plan should include validating the change using `run_python_file` on test files when available.
* **Security & Environment**: Never attempt to use or refer to functions or system operations outside of the listed tools. All file operations are restricted to the local `WORKING_DIR`. You can create, modify, or delete any file within this directory.
* **File Operations**: You can work with any file in the working directory - create new files, modify existing ones, or delete files as needed.
* dont use bold, italic or any other markdown in your responses
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
    ]
)

# Initialize chat history OUTSIDE the loop to maintain context
messages = []

# --- Main Agent Loop ---

if verbose_mode:
    print()
    print("  ╭─ Debug Mode ────────────────────────────────────────────────╮")
    print("  │   Verbose output enabled — showing tool calls & usage data  │")
    print("  ╰─────────────────────────────────────────────────────────────╯")

while True:
    user_prompt = input(f"\n  {USER_NAME}: ")
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
            print("Injected Project Metadata into chat history as system message.")

    # --- Agentic Loop (max 20 steps) ---
    for step in range(20):
        if verbose_mode:
            show_verbose_header(step + 1, "Calling model")

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=messages,
                config=types.GenerateContentConfig(
                    tools=[available_functions], system_instruction=system_prompt
                ),
            )
        except Exception as e:
            print(f"Error generating content: {e}")
            # Clean up history after a model error to allow a fresh start
            messages.pop()  # Remove the last user message
            if (
                len(messages) > 0 and messages[0].role == "system"
            ):  # Remove injected metadata if it's the only other thing
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

                # --- Clean UI for Function Call (Non-Verbose Mode) ---
                if func_name == "write_file":
                    # For write, only show the file path and that content is being written
                    display_args = f"file_path='{file_path}', content='...' (writing {len(func_args.get('content', ''))} chars)"
                elif func_name in ["run_python_file", "run_cpp_file", "run_js_file", "preview_html_file"]:
                    display_args = f"path='{file_path}'"
                elif file_path:
                    display_args = f"file_path='{file_path}'"
                else:
                    display_args = ", ".join(f"{k}='{v}'" for k, v in func_args.items())

                # Show a glance of the action for the end user
                print(f"  → {func_name}({file_path or 'context'})")

                # Show full arguments only in verbose mode
                if verbose_mode:
                    show_verbose_info("Function", f"{func_name}({func_args})")

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
                    else:
                        result = f"Error: Unknown function {func_name}"
                except Exception as e:
                    # Capture execution errors clearly for the model and user
                    result = f"ERROR executing {func_name}: {e}"

                # Print result to the user only in verbose mode
                if verbose_mode:
                    show_verbose_result(str(result))

                # 3. Feedback to agent (so it knows tool outcome) - ALWAYS send the result to the model
                messages.append(
                    types.Content(
                        role="user",
                        parts=[types.Part(text=f"Function call result: {result}")],
                    )
                )

        # 4. If final text output exists, finish loop
        elif response.text:
            print()
            print(f"  ╭─ {AGENT_NAME} ─────────────────────────────────────────────────╮")
            print()
            for line in response.text.split('\n'):
                print(f"    {line}")
            print()
            print("  ╰─────────────────────────────────────────────────────────────────╯")
            break

        # 5. Check for max steps
        if step == 19:
            print()
            print("  ╭─ Warning ───────────────────────────────────────────────────╮")
            print(f"  │   {AGENT_NAME} reached max steps ({step + 1}). Resetting...          │")
            print("  ╰─────────────────────────────────────────────────────────────╯")
            messages = []
            break

        # 6. Usage info each iteration if in verbose mode
        if verbose_mode and hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            total = usage.prompt_token_count + usage.candidates_token_count
            print()
            print("  ┌─ Token Usage ─────────────────────────────────────────────┐")
            print(f"  │  Prompt: {usage.prompt_token_count:,}  │  Response: {usage.candidates_token_count:,}  │  Total: {total:,}")
            print("  └───────────────────────────────────────────────────────────┘")
