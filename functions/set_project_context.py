import os
import json
from datetime import datetime
from google.genai import types

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PROJECT_DESCRIPTION_FILE


def set_project_context(working_directory, project_name, project_description=""):
    """
    Sets or updates the current project context in project_description.json.
    Use this when starting a new project or switching project focus.
    
    Args:
        working_directory: The root directory of the workspace
        project_name: Name of the current project (e.g., "calculator", "todo_app")
        project_description: Brief description of what the project does
    
    Returns:
        Success or error message
    """
    
    description_file = os.path.join(working_directory, PROJECT_DESCRIPTION_FILE)
    
    try:
        if os.path.exists(description_file):
            with open(description_file, "r", encoding="utf-8") as f:
                project_data = json.load(f)
        else:
            project_data = {
                "key_files": {},
                "debug_notes": {}
            }
        
        project_data["project_name"] = project_name
        project_data["project_summary"] = project_description
        project_data["last_updated"] = datetime.now().isoformat()
        project_data["active_folder"] = f"{project_name}/" if project_name else ""
        
        with open(description_file, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=4, ensure_ascii=False)
        
        return f"Project context updated: '{project_name}' - Files will be organized in '{project_name}/' folder"
    
    except Exception as e:
        return f"Error updating project context: {e}"


schema_set_project_context = types.FunctionDeclaration(
    name="set_project_context",
    description="Sets or updates the current project context. Call this when starting a new project to organize files in a dedicated folder, or to switch focus to an existing project.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "project_name": types.Schema(
                type=types.Type.STRING,
                description="Name of the project (e.g., 'calculator', 'todo_app', 'snake_game'). Use lowercase with underscores.",
            ),
            "project_description": types.Schema(
                type=types.Type.STRING,
                description="Brief 1-2 sentence description of what the project does.",
            )
        },
        required=["project_name"],
    ),
)
