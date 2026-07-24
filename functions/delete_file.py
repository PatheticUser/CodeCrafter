import os

from functions._security import validate_path


def delete_file(working_directory, file_path):
    """
    Safely deletes a file within the given working directory.
    Validates that the target file is within scope, exists, and is deletable.
    Returns a status message indicating success or failure.
    """

    # Security: path traversal check
    err = validate_path(working_directory, file_path)
    if err:
        return err

    target_file_abs = os.path.realpath(os.path.join(working_directory, file_path))

    # 2. Check existence
    if not os.path.exists(target_file_abs):
        return f'Error: File "{file_path}" not found.'

    # 3. Ensure it's a file, not a directory
    if not os.path.isfile(target_file_abs):
        return f'Error: "{file_path}" is not a file and cannot be deleted.'

    try:
        os.remove(target_file_abs)
        result_msg = f'Successfully deleted "{file_path}".'
        return result_msg
    except PermissionError:
        return f'Error: Permission denied while deleting "{file_path}".'
    except Exception as e:
        return f'Error deleting "{file_path}": {e}'


# --- OpenAI-compatible tool schema for Groq ---
schema_delete_file = {
    "type": "function",
    "function": {
        "name": "delete_file",
        "description": "Delete a file. Only operates within workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "File path relative to workspace.",
                },
            },
            "required": ["file_path"],
        },
    },
}
