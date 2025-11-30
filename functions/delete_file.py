import os
from google.genai import types


def delete_file(working_directory, file_path):
    """
    Safely deletes a file within the given working directory.
    Validates that the target file is within scope, exists, and is deletable.
    Returns a status message indicating success or failure.
    """

    # Normalize paths
    working_directory_abs = os.path.abspath(working_directory)
    target_file_abs = os.path.abspath(os.path.join(working_directory, file_path))

    # 1. Security check – prevent path traversal
    if not target_file_abs.startswith(working_directory_abs):
        return f'Error: Cannot delete "{file_path}" as it is outside the permitted working directory.'

    # 2. Check existence
    if not os.path.exists(target_file_abs):
        return f'Error: File "{file_path}" not found.'

    # 3. Ensure it’s a file, not a directory
    if not os.path.isfile(target_file_abs):
        return f'Error: "{file_path}" is not a file and cannot be deleted.'

    try:
        os.remove(target_file_abs)
        result_msg = f'Successfully deleted "{file_path}".'
        
        # 4. Auto-update project description (if enabled and not the description file itself)
        try:
            from config import AUTO_UPDATE_DESCRIPTION, PROJECT_DESCRIPTION_FILE
            if AUTO_UPDATE_DESCRIPTION and file_path != PROJECT_DESCRIPTION_FILE:
                from functions.update_project_description import update_project_description
                update_result = update_project_description(
                    working_directory, "delete", file_path
                )
                result_msg += f" | {update_result}"
        except Exception as e:
            result_msg += f" | Warning: Could not update project description: {e}"
        
        return result_msg
    except PermissionError:
        return f'Error: Permission denied while deleting "{file_path}".'
    except Exception as e:
        return f'Error deleting "{file_path}": {e}'


# --- Gemini / LLM Function Schema ---
schema_delete_file = types.FunctionDeclaration(
    name="delete_file",
    description="Delete a file safely within the working directory.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The path of the file to delete, relative to the working directory.",
            ),
        },
        required=["file_path"],
    ),
)
