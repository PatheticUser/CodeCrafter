import os

from src.tools._security import validate_path


def delete_file(working_directory, file_path):
    """
    Safely deletes a file within the given working directory.
    Validates that the target file is within scope, exists, and is deletable.
    """
    err = validate_path(working_directory, file_path)
    if err:
        return err

    target_file_abs = os.path.realpath(os.path.join(working_directory, file_path))

    if not os.path.exists(target_file_abs):
        return f'Error: File "{file_path}" not found.'

    if not os.path.isfile(target_file_abs):
        return f'Error: "{file_path}" is not a file and cannot be deleted.'

    try:
        os.remove(target_file_abs)
        return f'Successfully deleted "{file_path}".'
    except PermissionError:
        return f'Error: Permission denied while deleting "{file_path}".'
    except Exception as e:
        return f'Error deleting "{file_path}": {e}'


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
