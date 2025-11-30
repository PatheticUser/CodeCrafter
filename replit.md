# CodeCrafter - AI Coding Agent

## Overview
CodeCrafter is a local command-line AI coding agent powered by Google Gemini 2.5 Flash. It provides an interactive CLI interface for reading, writing, executing, and debugging code across multiple languages (Python, C++, JavaScript, HTML/CSS) within a sandboxed working directory.

**Current State:** Imported from external repository, ready for use in Replit environment.

**Purpose:** Learning tool and rapid prototyping assistant for software development tasks.

## Recent Changes
- **2025-11-30**: Initial import to Replit environment
  - Configured workflow for CLI-based interaction
  - Installed dependencies via uv (google-genai, python-dotenv, sift-stack-py)
  - Set up console-based workflow for the agent
  - Project uses pyproject.toml for dependency management

## User Preferences
- Not yet established - first session

## Project Architecture

### Core Components
1. **main.py**: Main agent loop and CLI interface
   - Handles conversation history with Gemini API
   - Implements agentic loop (max 20 iterations)
   - Provides verbose mode for debugging
   - Enforces security boundaries for file operations

2. **config.py**: Global configuration
   - WORKING_DIR: Points to "calculator/" sandbox directory
   - AUTO_UPDATE_DESCRIPTION: Enables automatic project metadata updates
   - MAX_FILE_CHARS: 10,000 character limit for file reads

3. **functions/**: Tool implementations
   - File operations: get_files_info, get_file_content, write_file, delete_file
   - Code execution: run_python_file, run_cpp_file, run_js_file
   - Preview: preview_html_file
   - Metadata: get_project_description, update_project_description

4. **calculator/**: Sandboxed working directory
   - Contains sample projects for testing
   - Currently has snake_game example

### Dependencies
- google-genai==1.12.1 (Gemini API SDK)
- python-dotenv==1.1.0 (Environment variable management)
- sift-stack-py>=0.9.1 (Additional utilities)
- Python 3.11+ required

### Security Features
- All file operations restricted to WORKING_DIR (calculator/ folder)
- Path validation prevents directory traversal
- 30-second timeout on code execution
- Environment variable management for API keys

### Environment Requirements
- GEMINI_API_KEY: Required for Gemini API access (stored as secret)

### CLI Usage
```bash
python main.py                    # Start agent
python main.py --verbose          # Enable debug mode
python main.py --rebuild-description  # Rebuild project metadata
```

### Supported Languages
- Python (execute with timeout)
- C++ (compile with g++ and execute)
- JavaScript (Node.js/Bun runtime)
- HTML/CSS (browser preview)

## Architecture Decisions
- **2025-11-30**: Using uv for Python package management (pyproject.toml)
- **2025-11-30**: Console-based workflow for CLI interaction
- **Initial design**: Sandboxed calculator/ directory for safe code execution
- **Initial design**: Function-calling architecture with Gemini for tool use
