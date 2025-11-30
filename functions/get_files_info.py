import os
from datetime import datetime
from google.genai import types


def make_function_schema(name, description, params):
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": params,
        },
    }


def get_files_info(working_directory, directory=".", verbose=True):
    """
    Recursively lists files in a directory (relative to working_directory),
    includes size and last modified time (without reading file content).
    Returns a list of dicts, or an error string if invalid.
    """

    files_info = []
    target_directory = os.path.join(working_directory, directory)

    # Normalize paths
    working_directory_abs = os.path.abspath(working_directory)
    target_directory_abs = os.path.abspath(target_directory)

    # 1. Validate path is within working directory
    if not target_directory_abs.startswith(working_directory_abs):
        return f'Error: Cannot list "{directory}" as it is outside the permitted working directory'

    # 2. Validate directory exists
    if not os.path.exists(target_directory_abs):
        return f'Error: "{directory}" does not exist'

    # 3. Validate path is a directory
    if not os.path.isdir(target_directory_abs):
        return f'Error: "{directory}" is not a directory'

    # Walk recursively
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


# --- Schema for function calling (Gemini / LLM integration) ---
schema_get_files_info = make_function_schema(
    name="get_files_info",
    description=(
        "Recursively lists files in the specified directory (relative to the working directory). "
        "Includes file size and modified date (without reading file content). "
        "Ensures directory stays within the working directory."
    ),
    params={
        "directory": {
            "type": types.Type.STRING,
            "description": (
                "The directory to list files from, relative to the working directory. "
                "If not provided, lists files in the working directory itself."
            ),
        },
        "verbose": {
            "type": types.Type.BOOLEAN,
            "description": "Whether to print detailed info for each file while scanning.",
        },
    },
)
