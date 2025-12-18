# CodeCrafter - AI Coding Agent

**Status:** Fully functional local AI coding agent for reading, writing, executing, and debugging code across multiple languages in an intelligently organized workspace.

**Latest Version:** v1.5.0 — Adaptive workspace management with intelligent project organization and friendly error handling.

**Model Used:** Google Gemini 2.5 Flash (via `google-genai` SDK)

**Supported Languages:** Python, C++, JavaScript, HTML/CSS

**Author:** Muhammad Rameez — [rameezalipacific@gmail.com](mailto:rameezalipacific@gmail.com)

If this project helped you, please give it a star on GitHub.

---

## Table of Contents

1. [What This Is](#what-this-is)
2. [Key Features](#key-features)
3. [What's New in v1.5.0](#whats-new-in-v150)
4. [Prerequisites & Installation](#prerequisites--installation)
5. [Quick Start Guide](#quick-start-guide)
6. [Project Architecture](#project-architecture)
7. [Workspace Organization](#workspace-organization)
8. [Interactive CLI Usage](#interactive-cli-usage)
9. [Available Tools & Functions](#available-tools--functions)
10. [Error Handling & API Management](#error-handling--api-management)
11. [Security & Safety](#security--safety)
12. [Troubleshooting](#troubleshooting)
13. [Best Practices](#best-practices)
14. [Future Improvements](#future-improvements)
15. [Contributing & Support](#contributing--support)

---

## What This Is

CodeCrafter is a **local command-line AI coding agent** that leverages Google Gemini 2.5 Flash to provide intelligent, interactive assistance with software development tasks. It operates in a sandboxed environment and can:

- **Read & Analyze Code** — Understand project structure and file contents with intelligent metadata tracking. The agent can analyze code patterns, identify dependencies, and provide contextual understanding.
- **Write & Modify Files** — Create new files or edit existing ones with automatic workspace organization. Supports creating complex multi-file projects with proper structure and organization.
- **Execute Code** — Run Python, C++, and JavaScript scripts with built-in error handling, timeouts, and full output capture for debugging and validation.
- **Preview Interfaces** — Open HTML/CSS files in browser for interactive design review. Automatically links stylesheets and provides live preview capabilities.
- **Manage Projects** — Automatically organize files into projects or keep simple files flat based on context. Maintains project metadata for future reference.
- **Maintain Context** — Track project metadata and history across conversations. Project descriptions are automatically generated and updated.
- **Handle Errors Gracefully** — Display friendly messages for API limits, connection issues, and request problems instead of raw error codes.

This tool is designed for **learning, rapid prototyping, and development assistance** — not for production use.

---

## Key Features

### 1. **Adaptive Workspace Management** (v1.5.0)

CodeCrafter intelligently organizes your workspace based on the type of request. This feature eliminates the need for manual organization and keeps your workspace clean and structured.

- **Project Requests** — When you ask for a complete project (e.g., "build a calculator app", "create a todo list"), all files are organized in a dedicated folder (e.g., `calculator/`, `todo_app/`). This keeps related files together and makes project navigation intuitive.
- **Simple File Requests** — When you ask for standalone scripts or utilities (e.g., "write a script to calculate fibonacci"), files are created directly in the workspace root. This keeps simple utilities accessible without unnecessary folder nesting.
- **Automatic Context** — The system automatically tracks the active project and maintains accurate metadata in `project_description.json`. This allows the agent to maintain context across multiple conversations.
- **Manual Control** — Use the `set_project_context` function to explicitly define or switch projects. This gives you full control when needed.

### 2. **Multi-Language Support**

CodeCrafter supports multiple programming languages with language-specific handling:

- **Python** — Execute Python scripts with 30-second timeout protection and full error reporting. Captures stdout, stderr, and exceptions for comprehensive debugging.
- **C++** — Compile C++ code with g++ compiler and execute the resulting binaries. Supports modern C++ standards with full compilation error reporting.
- **JavaScript** — Run JavaScript files using Node.js or Bun runtime. Supports both ES6+ syntax and CommonJS modules.
- **HTML/CSS** — Preview HTML files in your default browser with automatic CSS stylesheet linking. Perfect for testing frontend designs and layouts.

### 3. **Intelligent Project Metadata**

The system maintains comprehensive project metadata for better context understanding:

- **Auto-Tracking** — Automatically scans and builds project descriptions when new files are added. Uses intelligent analysis to identify file purposes.
- **File Summaries** — Generates intelligent summaries based on code analysis. Examines imports, class definitions, function declarations to understand file purpose.
- **Context Awareness** — Helps the AI understand project structure without reading every file. Makes token usage more efficient while maintaining context.
- **Manual Updates** — Use `set_project_context` to explicitly define project scope and description. Useful for providing domain-specific context.
- **Rebuild Capability** — Use the `--rebuild-description` flag to manually rebuild project metadata if needed.

### 4. **Friendly Error Handling** (v1.5.0)

Instead of cryptic error codes, the agent provides clear, actionable guidance:

- **API Quota Exceeded** — Clear message explaining the quota limit has been reached, with recommendations to wait or check billing settings.
- **Request Errors** — Descriptive messages for oversized or malformed requests with suggestions to simplify the query.
- **Service Issues** — Informative messages for service unavailability with guidance on when to retry.
- **Execution Timeouts** — Clear indication when code execution exceeds time limits with suggestions to optimize.

### 5. **Professional CLI Interface**

The command-line interface is designed for clarity and professionalism:

- **Nerd Font Icons** — Uses terminal symbols with ANSI color coding (cyan, magenta, green, yellow, red) for visual distinction and clarity.
- **Personalized Experience** — Greets you by name at startup for a welcoming interaction.
- **Clean Output** — Minimal, readable function call indicators and result summaries that are easy to follow.
- **Verbose Mode** — Detailed debugging information available when needed with `--verbose` flag.
- **Token Tracking** — Displays token usage statistics to help manage API quota consumption.

---

## What's New in v1.5.0

### Major Improvements

- [COMPLETED] **Adaptive Workspace** — Projects get dedicated folders for organization; simple files stay in root to keep workspace clean
- [COMPLETED] **Set Project Context** — New `set_project_context` function for explicit project management and scope definition
- [COMPLETED] **Friendly API Errors** — No more raw error codes; helpful guidance and suggestions instead
- [COMPLETED] **Updated Project Metadata** — `project_description.json` now includes `project_summary` and `active_folder` fields for better tracking
- [COMPLETED] **Enhanced System Prompt** — AI is now better at deciding when to organize files into projects vs. keeping them at root level
- [COMPLETED] **Improved Error Messages** — Service errors, quota issues, and request problems display user-friendly messages

### Breaking Changes

None — all existing projects continue to work without modification or updates needed.

---

## Prerequisites & Installation

### Requirements

- **Python 3.11+** (tested on 3.11 and newer)
- **Google Gemini API Key** — Get it free from [Google AI Developer Portal](https://ai.google.dev/). Free tier includes daily usage limits.
- **Package Manager** — `uv` (recommended for faster installation) or `pip`
- **C++ Compiler** (optional) — g++ for C++ support; should already be available on most systems
- **Node.js or Bun** (optional) — For JavaScript execution; highly recommended

### Installation

#### Option 1: Using `uv` (Recommended)

The `uv` package manager is much faster and simpler than pip:

```bash
git clone <your-repo-url>
cd codedrafter

# Install dependencies
uv pip install google-genai python-dotenv sift-stack-py

# Or sync using pyproject.toml
uv sync
```

#### Option 2: Using `pip`

Traditional pip installation with virtual environment:

```bash
git clone <your-repo-url>
cd codedrafter

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or: .venv\Scripts\activate  (Windows)

# Install packages
pip install --upgrade pip
pip install google-genai python-dotenv sift-stack-py
```

#### Option 3: On Replit (Recommended for Beginners)

1. Fork or import this repository to Replit
2. Replit automatically detects `pyproject.toml` and installs dependencies
3. Configure the Secrets (see Quick Start below)

---

## Quick Start Guide

### 1. Set Up Your API Key

**On Replit:** 
- Navigate to Secrets (lock icon in left sidebar)
- Add a new secret: `GEMINI_API_KEY = your_api_key_here`
- Keys are automatically loaded into the environment

**Locally:**
Create a `.env` file in the project root:
```bash
echo GEMINI_API_KEY=your_api_key_here > .env
```

**Getting Your Key:**
1. Visit [Google AI Studio](https://ai.google.dev/aistudio)
2. Click "Get API Key"
3. Create a new API key
4. Copy and paste into your environment

### 2. Run the Agent

**Using uv (Recommended):**
```bash
uv run python main.py
```

**Using Python directly:**
```bash
python main.py
```

**With verbose debugging:**
```bash
python main.py --verbose
```

**Rebuild project metadata:**
```bash
python main.py --rebuild-description
```

### 3. Interact with the Agent

When you start the agent, you'll see:

```
  CodeCrafter
  ────────────────────────────────────────────────
  Model: gemini-2.5-flash | Mode: Interactive

  Hello Rameez, ready to build something solid

  Your name (press Enter to confirm)
```

After entering your name, you're ready to start:

```
  Rameez: Create a calculator app with add and multiply functions
```

The agent will:
1. Analyze your request
2. Organize files appropriately (create `calculator/` folder)
3. Write the necessary code
4. Test the implementation
5. Provide feedback and next steps

Type `exit` or `quit` to end the session.

---

## Project Architecture

### Directory Structure

```
codedrafter/
├── main.py                              # Core agent loop and CLI interface
├── config.py                            # Global configuration settings
├── pyproject.toml                       # Dependency management (uv/pip)
├── replit.md                            # Replit-specific documentation
├── README.md                            # This comprehensive guide
│
├── functions/                           # Tool implementations and schemas
│   ├── config.py                        # Function-specific configuration
│   ├── get_files_info.py                # List files and retrieve metadata
│   ├── get_file_content.py              # Read file contents safely
│   ├── write_file.py                    # Create or modify files
│   ├── delete_file.py                   # Remove files safely
│   ├── run_python_file.py               # Execute Python scripts
│   ├── run_cpp_file.py                  # Compile and run C++ programs
│   ├── run_js_file.py                   # Execute JavaScript files
│   ├── preview_html_file.py             # Open HTML files in browser
│   ├── get_project_description.py       # Retrieve project metadata
│   ├── update_project_description.py    # Update metadata automatically
│   └── set_project_context.py           # Define project scope (NEW in v1.5.0)
│
└── workspace/                           # Sandboxed working directory
    ├── project_description.json         # Central metadata file
    └── [user projects]                  # Your files and projects
        ├── calculator/                  # Example: project folder
        │   ├── main.py                  # Entry point
        │   ├── tests.py                 # Test file
        │   └── utils.py                 # Utility functions
        ├── todo_app/                    # Example: another project
        │   ├── app.py                   # Main application
        │   └── database.py              # Data persistence
        └── simple_script.py              # Example: standalone file
```

### Core Components Explained

#### **main.py** (v1.5.0)
The heart of the agent containing:

- **CLI Interface** — Personalized greeting and command input with elegant formatting
- **Conversation Management** — Maintains conversation history up to 20 iterations for context
- **Function Calling** — Integrates with Gemini's function-calling system for tool execution
- **Error Handling** — Catches and displays friendly error messages for all failure modes
- **Verbose Mode** — Optional detailed debugging information for troubleshooting
- **Security** — Path validation and working directory boundary enforcement

Key configuration in main.py:
- VERSION tracks current release (now 1.5.0)
- Icons define terminal symbols for visual identification
- Colors provide ANSI color coding for output
- System prompt guides the AI's behavior

#### **config.py**
Global configuration file with:

```python
PROJECT_FOLDER_NAME = "workspace"           # Where projects are stored
WORKING_DIR = "./workspace"                 # Full path (auto-calculated)
PROJECT_DESCRIPTION_FILE = "project_description.json"  # Metadata filename
AUTO_UPDATE_DESCRIPTION = True              # Auto-track file changes
MAX_FILE_CHARS = 10000                      # Max chars to read per file
```

All configuration is centralized here for easy management.

#### **functions/** Directory
Each tool is implemented as a separate module:

- **File Operations** — `get_files_info`, `get_file_content`, `write_file`, `delete_file`
  - Each includes path validation for security
  - Auto-updates project metadata when applicable

- **Code Execution** — `run_python_file`, `run_cpp_file`, `run_js_file`
  - 30-second timeout protection for runaway processes
  - Full output and error capture
  - Cross-platform compatibility

- **Project Management** — `get_project_description`, `set_project_context`
  - Intelligent metadata generation
  - Context tracking for workspace organization

#### **workspace/** Directory
The sandboxed area where all projects live:

- Projects get folders for related files
- Standalone scripts remain at root level
- `project_description.json` tracks all files and metadata
- All operations restricted to this directory for security

---

## Workspace Organization

CodeCrafter uses **intelligent file organization** based on context. This section explains how organization decisions are made.

### Project-Based Organization

When you ask for a **project** (complete application or system), CodeCrafter creates a dedicated folder:

Examples of project requests:
- "Build a snake game"
- "Create a web scraper for news articles"
- "Develop a todo list application"
- "Make a calculator app"

Result structure:
```
workspace/
├── project_description.json (updated with project_name: "snake_game")
└── snake_game/
    ├── main.py              # Main entry point
    ├── constants.py         # Game constants
    ├── game_objects.py      # Class definitions
    └── tests.py             # Test suite
```

The AI automatically:
1. Creates a folder named after the project (lowercase, snake_case)
2. Organizes all related files inside
3. Updates `project_description.json` with the project context
4. Generates intelligent summaries for each file

### Simple File Organization

When you ask for a **simple utility or script**, files remain at root level:

Examples of simple requests:
- "Write a script to calculate fibonacci numbers"
- "Create a function to sort a list"
- "Make a Python script to parse CSV files"
- "Build a JavaScript function for string manipulation"

Result structure:
```
workspace/
├── project_description.json (remains generic)
├── fibonacci.py              (created directly at root)
├── csv_parser.py             (another utility)
└── string_utils.js           (JavaScript utility)
```

This keeps simple utilities accessible without unnecessary nesting.

### Managing Project Context

You can explicitly manage project scope during interaction:

**Switch to existing project:**
```
Rameez: Focus on the calculator project

Output:
Setting project context to 'calculator'
Files will be organized in 'calculator/' folder
```

**Create a new project:**
```
Rameez: Start a new project called expense_tracker

Output:
Creating new project 'expense_tracker'
Files will be organized in 'expense_tracker/' folder
```

**View current project:**
```
Rameez: What project are we working on?

Output:
Current workspace context:
- Active Project: calculator
- Files: main.py, utils.py, tests.py
- Status: Ready for modifications
```

### Project Metadata File

The `project_description.json` file tracks all workspace information:

```json
{
    "project_name": "calculator",
    "project_summary": "A command-line calculator supporting basic operations",
    "active_folder": "calculator/",
    "last_updated": "2025-12-16T12:34:56",
    "key_files": {
        "calculator/main.py": "Entry point with CLI interface",
        "calculator/utils.py": "Mathematical operation functions",
        "calculator/tests.py": "Unit tests for all operations"
    },
    "debug_notes": {}
}
```

This metadata helps the agent:
- Understand project structure without reading every file
- Make intelligent decisions about file organization
- Maintain context across multiple conversations
- Generate accurate project summaries

---

## Interactive CLI Usage

This section shows real-world examples of interacting with CodeCrafter.

### Example 1: Create a Complete Project

Creating a structured todo list application from scratch:

```
Rameez: Build me a todo list app with Python. I need to add, remove, 
        view todos, and save them to a JSON file.

[Set Project Context]
Setting project context to 'todo_app'
Files will be organized in 'todo_app/' folder

[Write Files]
Created: todo_app/main.py (234 lines)
Created: todo_app/storage.py (156 lines)
Created: todo_app/test_app.py (89 lines)

[Test Implementation]
Running tests...
All tests passed: 12/12

Output from CodeCrafter:
I've created a complete todo list application with three modules:
- main.py: CLI interface with add, remove, view, and list commands
- storage.py: JSON-based file storage with load/save functionality
- test_app.py: Comprehensive test suite

The app is fully functional. Try running 'python todo_app/main.py' to test it.
```

### Example 2: Debug Existing Code

Finding and fixing a bug in existing code:

```
Rameez: There's a bug in calculator/main.py. When I try to divide by zero,
        it crashes instead of showing an error message.

[Analyze Code]
Reading: calculator/main.py
Reading: calculator/utils.py

[Run Test]
Running: calculator/test_app.py
Error found on line 45: division without zero-check

[Fix Code]
Updated: calculator/utils.py
Added zero-check in divide function with proper error message

[Verify Fix]
Running: calculator/test_app.py
All tests passed: 8/8

Output from CodeCrafter:
Found the issue! The divide function on line 45 of utils.py didn't check
for zero before dividing. I've added a check that returns an error message
instead of crashing. All tests now pass successfully.
```

### Example 3: Explore and Understand Project

Understanding what's in the current workspace:

```
Rameez: Can you summarize what projects we have and what each one does?

[List Files]
Scanning workspace...

[Get Descriptions]
Reading project metadata...

Output from CodeCrafter:
Current workspace contains 3 projects:

1. calculator/ - A command-line calculator
   - Supports: addition, subtraction, multiplication, division
   - Tests: 8/8 passing
   - Files: main.py, utils.py, test_app.py

2. todo_app/ - Task management application
   - Features: add, remove, complete, list tasks
   - Storage: JSON file persistence
   - Files: main.py, storage.py, test_app.py

3. string_utils.py - Standalone utility module
   - Functions: reverse_string, is_palindrome, count_vowels
   - Standalone file: no project folder
```

### Example 4: Execute and Debug Code

Running code and debugging output:

```
Rameez: Run the calculator and test if 5 + 3 equals 8

[Execute]
Running: python calculator/main.py

Output:
> 5 + 3
Result: 8

CodeCrafter Output:
Execution successful! The calculator correctly computed 5 + 3 = 8.
All operations are working as expected.
```

---

## Available Tools & Functions

### File Operations

| Function | Purpose | Output | Security |
|----------|---------|--------|----------|
| `get_files_info` | List files and retrieve metadata (path, size, modification date) | File listing with metadata | Restricted to WORKING_DIR |
| `get_file_content` | Read file contents with automatic truncation for large files | File content (max 10000 chars) | Path validation, size limits |
| `write_file` | Create new files or modify existing ones; auto-updates metadata | Success message with char count | Creates parent directories, boundary check |
| `delete_file` | Remove files safely with metadata updates | Confirmation of deletion | Requires explicit request, boundary check |

### Code Execution

| Function | Purpose | Timeout | Output | Use Case |
|----------|---------|---------|--------|----------|
| `run_python_file` | Execute Python scripts with full error reporting | 30 seconds | stdout, stderr, exit code | Testing, debugging, utilities |
| `run_cpp_file` | Compile C++ with g++ and execute the binary | 30 seconds | Compilation output, runtime output | Performance testing, algorithms |
| `run_js_file` | Execute JavaScript with Node.js or Bun runtime | 30 seconds | stdout, stderr, exit code | Web utilities, data processing |
| `preview_html_file` | Open HTML file in default browser with CSS support | N/A | Browser window | UI/design testing, prototyping |

### Project Management

| Function | Purpose | Parameters | Returns |
|----------|---------|-----------|---------|
| `get_project_description` | Fetch and display current project metadata | Optional: file_path | JSON metadata with all file summaries |
| `set_project_context` | Define or switch project scope | project_name (required), description (optional) | Confirmation with folder path |

---

## Error Handling & API Management

### Friendly Error Messages (v1.5.0)

CodeCrafter displays user-friendly error messages instead of raw error codes, helping you understand what went wrong and what to do about it.

#### API Quota Exceeded

When you hit your API quota limit:

```
[WARNING] API Limit Reached
────────────────────────────────────────────────
You've hit your Gemini API quota for now.
Wait a minute and try again, or check your
Google AI Studio billing/plan settings.
```

What this means: You've used all your free API requests for the current period.

How to fix:
1. Wait for the quota to reset (daily for free tier)
2. Check your usage at https://aistudio.google.com/
3. Consider upgrading to a paid plan for higher limits

#### Request Error

When a request is too large or malformed:

```
[ERROR] Request Error
────────────────────────────────────────────────
The request was too large or malformed.
Try a simpler query or start fresh.
```

What this means: Your request exceeded size limits or had invalid parameters.

How to fix:
1. Break large requests into smaller tasks
2. Use simpler, clearer language
3. Type `exit` to start a fresh conversation

#### Service Temporarily Unavailable

When the Gemini API is overloaded:

```
[WARNING] Service Temporarily Unavailable
────────────────────────────────────────────────
Gemini API is experiencing high load.
Please wait a moment and try again.
```

What this means: The Gemini service is experiencing temporary issues.

How to fix:
1. Wait 1-2 minutes
2. Retry your request
3. If problem persists, check the Gemini status page

### API Quota Management

#### Understanding Your Quota

Free tier limits:
- 15 requests per minute
- 1.5 million tokens per day
- Quota resets daily at midnight UTC

Paid tier offers higher limits based on your plan.

#### Checking Your Usage

Visit [Google AI Studio Dashboard](https://aistudio.google.com/):
1. Click your profile in top right
2. Select "API Overview"
3. View current usage and quota

#### Optimizing Token Usage

To reduce token consumption:

1. **Use Project Metadata** — AI reads metadata instead of full files
2. **Be Specific** — Clearer requests need fewer iterations
3. **Break Tasks Down** — Multiple focused tasks use fewer tokens than vague requests
4. **Enable Verbose Mode** — See exactly how many tokens each request uses
5. **Reuse Context** — Keep conversations focused to avoid re-explaining

#### Upgrading Your Plan

For higher limits:
1. Visit [Google AI Studio](https://ai.google.dev/)
2. Click "Upgrade" in bottom left
3. Select your tier
4. Follow payment instructions

---

## Security & Safety

### Important Security Warnings

**Execution Risks**

CodeCrafter can execute arbitrary Python, C++, and JavaScript code. This enables powerful automation but entails risks:

- **Code Execution Power** — The agent can run any code in the working directory
- **File Access** — Can read, write, and delete any file in workspace
- **Never Run Untrusted Code** — Only use with trusted code from trusted sources
- **Isolated Environment** — Always use in isolated development environments
- **Sandbox Limitations** — While restricted to WORKING_DIR, code can still cause issues

### Sandbox Boundaries

All operations are restricted to `WORKING_DIR` (default: `./workspace`):

- **Read Operations** — Can only read files in WORKING_DIR
- **Write Operations** — Can only create/modify files in WORKING_DIR
- **Execute Operations** — Can only run code that accesses WORKING_DIR
- **Path Validation** — Attempts to escape sandbox are blocked

Example of what's blocked:
```python
# These will be rejected by path validation:
../sensitive_file.txt                    # Directory traversal blocked
/etc/passwd                              # Absolute paths blocked
~/.ssh/id_rsa                            # Home directory access blocked
```

### Best Security Practices

1. **Use Isolated Directories** — Keep WORKING_DIR in a test/development area
2. **Review Generated Code** — Always inspect code before execution
3. **Enable Verbose Mode** — Monitor all tool calls with `--verbose`
4. **Keep API Key Secure** — Never commit `.env` or hardcode credentials
5. **Disable Untrusted Tools** — Remove tools you don't need from `main.py`
6. **Regular Backups** — Backup important files before allowing modifications
7. **Monitor Execution** — Watch output from code execution closely

### Production Use

**NOT RECOMMENDED for production** for these reasons:

- Security: Code execution in production could be catastrophic
- Reliability: AI-generated code may have edge cases
- Cost: API quota management becomes complex at scale
- Compliance: Generated code may not meet compliance requirements

Use CodeCrafter only for:
- Development and testing
- Learning and experimentation
- Prototyping and rapid iteration
- Educational purposes

---

## Troubleshooting

### Common Issues and Solutions

#### "GEMINI_API_KEY not found"

**Problem:** The API key is not configured or not accessible.

**Solution:**
- On Replit: Add key to Secrets (lock icon in sidebar)
- Locally: Create `.env` file with `GEMINI_API_KEY=your_key`
- Verify: Check that `.env` is in the same directory as `main.py`
- Don't commit: Add `.env` to `.gitignore`

#### "ModuleNotFoundError: No module named 'google'"

**Problem:** Required packages are not installed.

**Solution:**
```bash
# Using uv
uv pip install google-genai python-dotenv

# Using pip
pip install google-genai python-dotenv
```

#### "API Quota Exceeded (429)"

**Problem:** You've used all available API requests.

**Solution:**
1. Wait a few minutes (free tier resets daily)
2. Check usage at [Google AI Studio](https://aistudio.google.com/)
3. Upgrade to a paid plan for higher limits
4. Optimize queries to use fewer tokens

#### "Timeout: Script took longer than 30 seconds"

**Problem:** Code execution exceeded the timeout limit.

**Solution:**
1. Optimize the code for performance
2. Break long operations into chunks
3. Add progress indicators so timeout isn't silent
4. Increase timeout in `functions/run_python_file.py` if needed (not recommended)

#### "Files appearing in wrong project folder"

**Problem:** Files are organized incorrectly or in wrong locations.

**Solution:**
```bash
# Rebuild project metadata to rescan workspace
python main.py --rebuild-description
```

#### "Connection refused when trying to preview HTML"

**Problem:** Browser preview is not working.

**Solution:**
1. Check if default browser is configured
2. Try manually opening the HTML file
3. Verify file path is correct
4. Check file permissions

#### "Strange characters in output"

**Problem:** Terminal doesn't support Nerd Font symbols.

**Solution:**
1. Update your terminal to support Nerd Fonts
2. Or modify `main.py` to use simpler symbols
3. Output will still work, just without icons

### Debug Mode

Enable verbose logging for detailed troubleshooting:

```bash
python main.py --verbose
```

Verbose mode shows:
- Complete function arguments
- Full API request details
- Detailed token usage per request
- Complete response summaries
- Error backtraces

This is invaluable for understanding what's happening internally.

---

## Best Practices

### 1. Writing Effective Prompts

**Good Prompts (Specific and Clear)**
```
Rameez: Create a Python function that takes a list of numbers and returns
        the sum of all even numbers. Include error handling for invalid input.
```

**Poor Prompts (Vague)**
```
Rameez: Write some code
```

Why good prompts matter:
- AI understands exactly what you want
- Fewer iterations needed
- Better quality results
- Lower token usage

### 2. Breaking Down Complex Tasks

**Effective Approach**
```
Rameez: First, create a basic calculator class with add, subtract, multiply, divide
Rameez: Next, add error handling for division by zero
Rameez: Then, create a test file to verify all operations work correctly
```

**Less Effective**
```
Rameez: Build a complete calculator with all features and tests
```

Benefits:
- Each step is focused
- Easier to debug if something fails
- AI can provide feedback on each step
- More transparent progress

### 3. Providing Context

**With Context**
```
Rameez: I'm building a web scraper for e-commerce sites. Can you add
        rate limiting and error retry logic so we don't overwhelm servers?
```

**Without Context**
```
Rameez: Add rate limiting and retry logic to my scraper
```

Benefits:
- AI understands the domain
- Suggestions are more appropriate
- Code quality improves
- Fewer iterations needed

### 4. Using Verbose Mode

When debugging or learning:

```bash
python main.py --verbose
```

Shows:
- Exactly which functions are being called
- What parameters are being passed
- Complete results before displaying
- Token usage per request
- Time tracking

### 5. Maintaining Project Organization

- Use `set_project_context` to group related work
- Keep project names descriptive (e.g., `expense_tracker`, not `proj1`)
- Use `--rebuild-description` occasionally to keep metadata accurate
- Review `project_description.json` to understand structure

### 6. Testing and Validation

Always validate AI-generated code:

```
Rameez: Write a sorting algorithm, then run tests to verify it works correctly
```

Or after code generation:

```
Rameez: Run the tests in calculator/test_app.py and show me the results
```

---

## Future Improvements

Potential enhancements planned for future versions:

**Data Persistence**
- Save conversation history across sessions
- Persistent memory of user preferences
- Project-specific notes and documentation

**Advanced Testing**
- Integration with pytest for automated testing
- Coverage analysis and reporting
- Performance profiling and optimization suggestions

**Code Quality**
- AI-powered code review and suggestions
- Style checking and formatting
- Security vulnerability scanning

**Version Control**
- Git integration for automatic commits
- Diff analysis and intelligent messaging
- Branch management suggestions

**Deployment**
- Direct deployment to cloud platforms (Heroku, AWS, etc.)
- Docker containerization support
- Build and CI/CD automation

**Collaboration**
- Share projects with team members
- Collaborative editing sessions
- Comment and annotation support

**Extensions**
- Custom tool registration system
- Plugin architecture for third-party integrations
- Marketplace for community-built extensions

---

## Contributing & Support

### Reporting Issues

Found a bug? We'd love to hear about it. Create an issue with:

**Required Information:**
- Clear description of the problem
- Steps to reproduce
- Expected vs. actual behavior
- Error messages or logs
- Your environment (Python version, OS, terminal)

**Example Issue Report:**
```
Title: Calculator crashes when adding large numbers

Description: When I try to add two numbers larger than 1 million,
the calculator crashes with "OverflowError".

Steps to reproduce:
1. Create a calculator project
2. Run calculator/main.py
3. Enter "999999999 + 999999999"

Expected: Should display the sum
Actual: Crashes with OverflowError

Environment: Python 3.11, macOS 12, Replit
```

### Suggesting Features

Have an idea? We want to hear it. Include:

- What you want to do
- Why it would be useful
- How you'd like it to work
- Any examples or mockups

**Example Feature Request:**
```
Title: Add JavaScript execution support

Description: Would love to run JavaScript files for testing algorithms
and utilities without leaving the agent.

Use Case: Testing string manipulation utilities and data sorting before
integrating into projects.

Proposed Syntax:
Rameez: Run the JavaScript file utils.js and test the sort function
```

### Getting Help

- **Documentation** — Read this README thoroughly
- **Troubleshooting** — See the Troubleshooting section above
- **Verbose Mode** — Use `--verbose` flag for debugging
- **Contact** — Email [rameezalipacific@gmail.com](mailto:rameezalipacific@gmail.com)

### Contributing Code

Want to contribute? We welcome contributions:

1. **Fork** the repository
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** with clear commit messages
4. **Test thoroughly** before submitting
5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Create a Pull Request** with description of changes

**Contribution Guidelines:**
- Follow existing code style
- Add comments for complex logic
- Include error handling
- Test new features thoroughly
- Update documentation if needed

### License

This project is licensed under the MIT License. See LICENSE file for details.

The MIT License allows you to:
- Use the code for any purpose (personal, commercial)
- Modify the code
- Distribute the code
- Use privately

With the requirement:
- Include the license and copyright notice

---

## Acknowledgments

### Technologies & Services

- **Google Gemini 2.5 Flash** — Powerful multimodal AI model powering the agent
- **google-genai SDK** — Official Python SDK for seamless API integration
- **Replit** — Cloud development environment and deployment platform
- **Open Source Community** — Inspiration, tools, and support

### Special Thanks

- Contributors who have submitted bug reports and feature requests
- Users who provided feedback and helped improve the tool
- The open source community for amazing tools and libraries

---

## Quick Reference

### Command Cheat Sheet

```bash
# Start the agent
python main.py
uv run python main.py

# Debug mode
python main.py --verbose

# Rebuild metadata
python main.py --rebuild-description

# Quit session
exit
quit
```

### Project Examples

```
# Create project
Rameez: Build a snake game with Python

# Work on existing project
Rameez: Add high score tracking to the game

# Simple script
Rameez: Write a script to convert CSV to JSON

# Debug code
Rameez: Fix the bug in main.py on line 45

# Run tests
Rameez: Execute the test suite and show results
```

### File Organization Examples

```
workspace/
├── calculator/              # Project: complex system
│   ├── main.py
│   ├── utils.py
│   └── tests.py
├── snake_game/              # Project: standalone app
│   ├── main.py
│   └── constants.py
├── fibonacci.py             # Simple: standalone script
└── csv_parser.py            # Simple: utility function
```

---

**Last Updated:** December 16, 2025 | **Version:** 1.5.0 | **Author:** Muhammad Rameez
