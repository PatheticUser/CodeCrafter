import os
import json
import sys
from datetime import datetime

# Import global config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PROJECT_DESCRIPTION_FILE


def update_project_description(working_directory, operation, file_path, content_preview=""):
    """
    Auto-updates the project_description.json file when files are added, modified, or deleted.
    
    Args:
        working_directory: The root directory of the project
        operation: Type of operation ('add', 'modify', 'delete')
        file_path: Relative path of the file that changed
        content_preview: Optional preview of file content for generating summary
    
    Returns:
        Success or error message
    """
    
    description_file = os.path.join(working_directory, PROJECT_DESCRIPTION_FILE)
    
    try:
        # Load existing description
        if os.path.exists(description_file):
            with open(description_file, "r", encoding="utf-8") as f:
                project_data = json.load(f)
        else:
            # Create new structure if file doesn't exist
            project_data = {
                "project_name": os.path.basename(working_directory),
                "last_updated": datetime.now().isoformat(),
                "key_files": {},
                "debug_notes": {}
            }
        
        # Ensure key_files exists
        if "key_files" not in project_data:
            project_data["key_files"] = {}
        
        # Update based on operation
        if operation == "delete":
            # Remove file from key_files
            if file_path in project_data["key_files"]:
                del project_data["key_files"][file_path]
        
        elif operation in ["add", "modify"]:
            # Generate a simple summary based on file content preview
            summary = generate_file_summary(file_path, content_preview)
            project_data["key_files"][file_path] = summary
        
        # Update timestamp
        project_data["last_updated"] = datetime.now().isoformat()
        
        # Write back to file
        with open(description_file, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=4, ensure_ascii=False)
        
        return f"Successfully updated project_description.json: {operation} operation on {file_path}"
    
    except Exception as e:
        return f"Error updating project_description.json: {e}"


def generate_file_summary(file_path, content_preview):
    """
    Generates a brief summary of what a file does based on its path and content preview.
    
    Args:
        file_path: The relative path of the file
        content_preview: Preview of the file content (first few lines or full content)
    
    Returns:
        A 1-2 line summary string
    """
    
    # Extract file extension and name
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1]
    
    # Try to extract meaningful info from content
    lines = content_preview.split('\n')[:20]  # First 20 lines
    
    # Look for common patterns
    is_config = file_ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg']
    is_test = 'test' in file_name.lower() or any('import unittest' in line or 'import pytest' in line for line in lines)
    is_main = file_name in ['main.py', '__main__.py', 'app.py', 'run.py']
    
    # Look for class/function definitions
    classes = [line.strip() for line in lines if line.strip().startswith('class ')]
    functions = [line.strip() for line in lines if line.strip().startswith('def ')]
    
    # Generate summary
    if is_config:
        return f"Configuration file for {file_name.replace('_', ' ').replace('.', ' ')} settings"
    elif is_test:
        return f"Test file containing unit/integration tests for validating functionality"
    elif is_main:
        return f"Entry point script that orchestrates the application and handles initialization"
    elif classes:
        class_name = classes[0].split('class ')[1].split(':')[0].split('(')[0].strip()
        return f"Defines the '{class_name}' class with core business logic and methods"
    elif functions:
        func_count = len(functions)
        return f"Utility module with {func_count} function(s) for {file_name.replace('_', ' ').replace('.py', '')} operations"
    else:
        # Generic summary based on file name
        name_parts = file_name.replace('_', ' ').replace('.py', '').replace('.js', '')
        return f"Module handling {name_parts} functionality"


def scan_and_rebuild_description(working_directory):
    """
    Scans all files in the working directory and rebuilds the project_description.json.
    Useful for initializing or resetting the project description.
    
    Args:
        working_directory: The root directory of the project
    
    Returns:
        Success or error message
    """
    
    try:
        project_data = {
            "project_name": os.path.basename(working_directory),
            "last_updated": datetime.now().isoformat(),
            "key_files": {},
            "debug_notes": {}
        }
        
        # Walk through all files
        for root, dirs, files in os.walk(working_directory):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                # Skip hidden files and compiled Python files
                if file.startswith('.') or file.endswith('.pyc'):
                    continue
                
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, working_directory)
                
                # Read first part of file for summary
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content_preview = f.read(2000)  # First 2000 chars
                    
                    summary = generate_file_summary(relative_path, content_preview)
                    project_data["key_files"][relative_path] = summary
                except:
                    # If can't read (binary file, etc), just note its existence
                    project_data["key_files"][relative_path] = f"Binary or unreadable file: {file}"
        
        # Write to project description file
        description_file = os.path.join(working_directory, PROJECT_DESCRIPTION_FILE)
        with open(description_file, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=4, ensure_ascii=False)
        
        return f"Successfully scanned and rebuilt project_description.json with {len(project_data['key_files'])} files"
    
    except Exception as e:
        return f"Error rebuilding project_description.json: {e}"
