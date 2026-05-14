import os


def write_file(working_directory, file_path, content):
    """
    Safely writes to a file within working_directory.
    Creates the file if it doesn't exist.
    """
    working_directory_abs = os.path.abspath(working_directory)
    target_file_abs = os.path.abspath(os.path.join(working_directory, file_path))

    if not (
        target_file_abs == working_directory_abs
        or target_file_abs.startswith(working_directory_abs + os.sep)
    ):
        return f'Error: Cannot write to "{file_path}" as it is outside the permitted working directory'

    try:
        parent_dir = os.path.dirname(target_file_abs)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
    except Exception as e:
        return f"Error: Failed to create directories for {file_path}: {e}"

    try:
        with open(target_file_abs, "w", encoding="utf-8") as f:
            f.write(content)

        return (
            f'Successfully wrote to "{file_path}" ({len(content)} characters written)'
        )
    except Exception as e:
        return f"Error: Failed to write to {file_path}: {e}"


schema_write_file = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": (
            "Safely writes the provided content to a file within the working directory. "
            "Creates the file and any missing directories if necessary. "
            "Returns a success or error message."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The relative path of the file to write inside the working directory.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write into the file.",
                },
            },
            "required": ["file_path", "content"],
        },
    },
}
