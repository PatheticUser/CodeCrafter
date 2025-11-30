
# CodeCrafter - AI Coding Agent

**Status:** Fully working local AI coding agent for reading, writing, executing, and debugging Python, C++, JavaScript, and HTML/CSS code in a sandboxed working directory.

**Model Used:** Google Gemini 2.5 Flash (via `google-genai` SDK)

**Supported Languages:** Python, C++, JavaScript, HTML/CSS

**Author:** Muhammad Rameez — [rameezalipacific@gmail.com](mailto:rameezalipacific@gmail.com)

If this project helped you, please give it a star <3

## Recent Changes
- **2025-11-23**: HTML/CSS preview support
  - Added `preview_html_file` tool for opening HTML files in browser
  - Automatic CSS file support when referenced in HTML
  - Browser-based preview using default web browser
  - Consistent workflow with other languages

- **2025-11-22**: Multi-language support extension
  - Added C++ support with compile and execute functionality (g++)
  - Added JavaScript support with Node.js and Bun runtime options
  - Updated system prompt and tool registration for new languages
  - Maintained same workflow for consistent multi-language experience
  
- **2025-10-19**: Initial setup in Replit environment
  - Fixed hardcoded Windows path to use dynamic cross-platform path
  - Configured workflow for console-based CLI interaction
  - Installed required dependencies (google-genai, python-dotenv)
  - Added GEMINI_API_KEY to environment secrets
  - Created global config.py for centralized project settings
  - Implemented auto-update system for project_description.json
  - Added intelligent file summary generation
  - Integrated auto-update into write_file and delete_file operations

***

## Table of Contents

1. What this is  
2. High-level Design & Features  
3. Safety First — Important Notices  
4. Prerequisites & Installation  
5. Quick Setup Instructions  
6. Project Architecture & Layout  
7. How to Use — CLI Examples  
8. Tools & Function-Calling (Technical Details)  
9. Testing — What to Create and Run  
10. Troubleshooting Common Issues  
11. Best Practices for Using AI Coding Agents  
12. Tips for Extension & Improvements  
13. Contributing, License & Contact  

***

## 1. What this is

CodeCrafter is a local command-line interface (CLI) AI coding agent built on Google Gemini 2.5 Flash using the `google-genai` SDK. It enables iterative problem-solving with function-calling to:

- List files and read their metadata/content in a sandboxed working directory  
- Write, modify, and delete files with safety checks  
- Execute Python scripts with a 30-second timeout  
- Compile and execute C++ programs using g++
- Run JavaScript files using Node.js or Bun runtime
- Preview HTML files with CSS support in web browser
- Engage interactively to inspect code, request bug fixes, run tests, and generate new code  

This tool is designed primarily for **learning** and **rapid prototyping**, not production use.

***

## 2. High-level Design & Features

The agent follows the **Observe-Act** loop: the AI model selects and executes functions (tools) to fulfill user goals iteratively.

### Core Tools

| Tool Name            | Description                                                 |
|----------------------|-------------------------------------------------------------|
| `get_files_info`     | Lists files and metadata (path, size KB, modified date)     |
| `get_file_content`   | Reads file content with truncation for large files          |
| `write_file`         | Creates/overwrites files; auto-updates project metadata     |
| `run_python_file`    | Executes Python scripts, capturing stdout/stderr; 30s timeout |
| `run_cpp_file`       | Compiles and executes C++ code using g++; 30s timeout |
| `run_js_file`        | Executes JavaScript using Node.js or Bun; 30s timeout |
| `preview_html_file`  | Opens HTML files in browser with CSS support |
| `delete_file`        | Deletes files; updates metadata                              |
| `get_project_description` | Fetches intelligent project metadata                    |
| `update_project_description` | Auto-updates project metadata with file summaries     |

### Agentic Loop

- Maintains conversation history up to 20 iterations.  
- Calls functions via LLM-driven function-calling integration.  
- Appends results as observations for iterative problem-solving.

### CLI Flags

- `--verbose`: Detailed debug logs including tool usage and LLM prompts.  
- `--usage`: Token usage statistics.  
- `--rebuild-description`: Rebuilds project metadata manually.  
- `q` or `exit`: Quit the agent session.

***

## 3. Safety First — Important Notices

**Execution Power & Risks**  

The agent can execute arbitrary Python code inside the working directory. This enables powerful automation but entails risks:

- **Never run with untrusted code** to avoid security vulnerabilities.  
- Enforced path validation restricts access to the configured `WORKING_DIR`.  
- Python execution has a 30-second timeout to avoid runaway processes.  
- Use only isolated or test projects for safe operation.  
- Disable Python execution by unregistering the `run_python_file` tool if desired.

***

## 4. Prerequisites & Installation

### Requirements

- Python 3.10+ (tested on 3.11)  
- Google Gemini API key (`GEMINI_API_KEY`) — obtain from [Google AI Developer Portal](https://ai.google.dev/pricing)  
- Python packages: `google-genai`, `python-dotenv`  

### Setup Steps

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows cmd.exe
.venv\Scripts\activate.bat

pip install --upgrade pip
pip install google-genai python-dotenv
```

***

## 5. Quick Setup Instructions

```bash
git clone <your-repo-url>
cd <repo-directory>

# activate virtual environment (see above)

echo GEMINI_API_KEY=sk-... > .env

# Confirm working directory in config.py (default: 'calculator/')

python main.py
```

***

## 6. Project Architecture & Layout

```plaintext
.
├── main.py                # CLI agent, loop, function registrations, security
├── config.py              # Global settings (working directory, toggles)
├── functions/             # Tool function definitions
│   ├── get_files_info.py
│   ├── get_file_content.py
│   ├── write_file.py
│   └── run_python_file.py
├── calculator/            # Sandboxed example working directory
│   ├── main.py            # Sample executable script
│   └── pkg/               # Example package & tests folder
└── README.md              # Documentation
```

### Main Components
1. **config.py**: Global configuration file
   - PROJECT_FOLDER_NAME: Name of the working directory (default: "calculator")
   - WORKING_DIR: Full path to the working directory
   - PROJECT_DESCRIPTION_FILE: Name of the metadata file
   - AUTO_UPDATE_DESCRIPTION: Enable/disable auto-updates (default: True)
   - MAX_FILE_CHARS: Max characters to read from files

2. **main.py**: Core agent loop and CLI interface
   - Handles user input/output
   - Manages conversation history with Gemini model
   - Implements security checks for file operations
   - Enforces working directory boundaries
   - Auto-creates project_description.json if missing

3. **functions/**: Tool definitions for agent capabilities
   - `get_files_info.py`: Lists files and metadata
   - `get_file_content.py`: Reads file contents
   - `write_file.py`: Creates/modifies files (auto-updates metadata)
   - `run_python_file.py`: Executes Python scripts (30s timeout)
   - `run_cpp_file.py`: Compiles and executes C++ programs (30s timeout)
   - `run_js_file.py`: Executes JavaScript files with Node.js/Bun (30s timeout)
   - `preview_html_file.py`: Opens HTML files in browser with CSS support
   - `delete_file.py`: Removes files (auto-updates metadata)
   - `get_project_description.py`: Fetches project metadata
   - `update_project_description.py`: Auto-updates project metadata with intelligent summaries

4. **calculator/**: Example working directory
   - Sample project for testing the agent
   - Contains calculator implementation with tests
   - Demonstrates agent capabilities

### Security Features
- All file operations restricted to WORKING_DIR (calculator/ folder)
- Path validation prevents directory traversal attacks
- File access control via project_description.json whitelist
- 30-second timeout on Python script execution


***

## 7. How to Use — CLI Examples

Prompt prefix:

```plaintext
Rameez:
```

Sample commands:

- Ask about code behavior:  
  `Rameez: How does main.py handle input parsing?`

- Request bug fixes:  
  `Rameez: Fix the bug where 3 + 7 * 2 incorrectly outputs 20.`

- Run tests and retrieve results:  
  `Rameez: Run the tests in calculator/pkg/tests.py and show results.`

- List project files:  
  `Rameez: What files are in this project?`

***

## 8. Tools & Function-Calling (Technical Details)

Supports careful JSON schema validation for parameters, ensuring compatibility with Gemini's function-calling system. The agent appends tool outputs correctly to prevent protocol errors.

***

## 9. Testing — What to Create & Run

- Create large text file (`calculator/lorem.txt`) to test truncation  
- Write-read cycles with `write_file` and `get_file_content`  
- Run Python scripts with and without CLI arguments  
- Test directory boundary enforcement by attempting unauthorized reads/writes  

***

## 10. Troubleshooting & Common Issues

- `ModuleNotFoundError`: Ensure `google-genai` is installed in the active environment.  
- `400 INVALID_ARGUMENT`: Double-check function parameters in schema vs. Python code.  
- Windows path issues: Use absolute paths with `os.path.abspath`.  
- Parameter mismatches in function calls cause errors — consistent naming required.

***

## 11. Best Practices for Using AI Coding Agents

- Provide detailed, clear, and specific prompts to the agent to get best results.  
- Break complex tasks into smaller, stepwise sub-tasks.  
- Provide relevant code context, docs, or examples for more accurate assistance.  
- Use verbose logging and stepwise debugging for improved transparency.  
- Regularly update project metadata using `--rebuild-description` for context accuracy.  
- Limit scope to sandboxed directories for safety and performance.  

***

## 12. Tips for Extension & Improvements

- Add auto-debug & repair loops that iteratively fix failing tests.  
- Integrate persistent memory stores to maintain context across sessions.  
- Enhance sandbox security via containerization or low-privilege user execution.  
- Add interactive confirmation steps for file-writing and running code.  
- Formalize testing using `pytest` or `unittest` for stability.  

***

## 13. Contributing, License & Contact

- Star the repo to support maintenance and development!  
- Licensed under the MIT License. Creating a LICENSE file is recommended.  
- Contact Muhammad Rameez: [rameezalipacific@gmail.com](mailto:rameezalipacific@gmail.com)  
- Contributions & fork messages are welcomed and appreciated.

## Safety Notes
- Never run untrusted code with this agent
- The agent can execute arbitrary Python code within the working directory
- All operations are logged for transparency
- Keep the working directory restricted to test/development projects


***
