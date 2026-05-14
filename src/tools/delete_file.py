import os


def delete_file(working_directory, file_path):
    """
    Safely deletes a file within the given working directory.
    Validates that the target file is within scope, exists, and is deletable.
    """
    working_directory_abs = os.path.abspath(working_directory)
    target_file_abs = os.path.abspath(os.path.join(working_directory, file_path))

    if not (
        target_file_abs == working_directory_abs
        or target_file_abs.startswith(working_directory_abs + os.sep)
    ):
        return f'Error: Cannot delete "{file_path}" as it is outside the permitted working directory.'

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
        "description": "Delete a file safely within the working directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path of the file to delete, relative to the working directory.",
                },
            },
            "required": ["file_path"],
        },
    },
}
