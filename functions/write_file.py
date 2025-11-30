import os
from google.genai import types


def write_file(working_directory, file_path, content):
    """
    Safely writes to a file within working_directory.
    Creates the file if it doesn't exist.
    Auto-updates project_description.json if enabled.
    Returns success message or error string.
    """

    # Normalize paths
    working_directory_abs = os.path.abspath(working_directory)
    target_file_abs = os.path.abspath(os.path.join(working_directory, file_path))

    # 1. Validate scope
    if not target_file_abs.startswith(working_directory_abs):
        return f'Error: Cannot write to "{file_path}" as it is outside the permitted working directory'

    # 2. Ensure parent directories exist
    try:
        parent_dir = os.path.dirname(target_file_abs)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
    except Exception as e:
        return f"Error: Failed to create directories for {file_path}: {e}"

    # Check if this is a new file or modification
    is_new_file = not os.path.exists(target_file_abs)
    
    # 3. Write the content
    try:
        with open(target_file_abs, "w", encoding="utf-8") as f:
            f.write(content)
        
        result_msg = f'Successfully wrote to "{file_path}" ({len(content)} characters written)'
        
        # 4. Auto-update project description (if enabled and not the description file itself)
        try:
            from config import AUTO_UPDATE_DESCRIPTION, PROJECT_DESCRIPTION_FILE
            if AUTO_UPDATE_DESCRIPTION and file_path != PROJECT_DESCRIPTION_FILE:
                from functions.update_project_description import update_project_description
                operation = "add" if is_new_file else "modify"
                content_preview = content[:2000]  # First 2000 chars for summary
                update_result = update_project_description(
                    working_directory, operation, file_path, content_preview
                )
                result_msg += f" | {update_result}"
        except Exception as e:
            result_msg += f" | Warning: Could not update project description: {e}"
        
        return result_msg
    except Exception as e:
        return f"Error: Failed to write to {file_path}: {e}"


# --- Schema for Gemini / LLM function calling ---
def make_function_schema(name, description, params):
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": params,
        },
    }


schema_write_file = make_function_schema(
    name="write_file",
    description=(
        "Safely writes the provided content to a file within the working directory. "
        "Creates the file and any missing directories if necessary. "
        "Returns a success or error message."
    ),
    params={
        "file_path": {
            "type": types.Type.STRING,
            "description": "The relative path of the file to write inside the working directory.",
        },
        "working_directory": {
            "type": types.Type.STRING,
            "description": "The root directory that scopes file writes. Files outside this directory are not allowed.",
        },
        "content": {
            "type": types.Type.STRING,
            "description": "The content to write into the file.",
        },
    },
)
