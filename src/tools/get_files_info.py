import os
from datetime import datetime

from src.tools._security import validate_directory


def get_files_info(working_directory, directory=".", verbose=True):
    """
    Recursively lists files in a directory (relative to working_directory),
    includes size and last modified time (without reading file content).
    Returns a list of dicts, or an error string if invalid.
    """
    err = validate_directory(working_directory, directory)
    if err:
        return err

    files_info = []
    working_directory_abs = os.path.realpath(working_directory)
    target_directory_abs = os.path.realpath(os.path.join(working_directory, directory))

    if not os.path.exists(target_directory_abs):
        return f'Error: "{directory}" does not exist'

    if not os.path.isdir(target_directory_abs):
        return f'Error: "{directory}" is not a directory'

    for root, _, files in os.walk(target_directory_abs):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, working_directory_abs)

            try:
                stats = os.stat(file_path)
                file_size_kb = round(stats.st_size / 1024, 2)
                modified_time = datetime.fromtimestamp(stats.st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                if verbose:
                    print(
                        f"Found: {relative_path} | Size: {file_size_kb} KB | Modified: {modified_time}"
                    )

                files_info.append(
                    {
                        "path": relative_path,
                        "size_kb": file_size_kb,
                        "modified": modified_time,
                    }
                )

            except Exception as e:
                print(f"Error reading metadata for {file_path}: {e}")

    if verbose:
        print(f"Total files found: {len(files_info)}")

    return files_info


schema_get_files_info = {
    "type": "function",
    "function": {
        "name": "get_files_info",
        "description": "List files in a directory with sizes and dates. Stays inside workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory to list, relative to workspace. Default: workspace root.",
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Print detailed info per file.",
                },
            },
            "required": [],
        },
    },
}
