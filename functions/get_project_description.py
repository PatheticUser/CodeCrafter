import os
import json
from google.genai import types


def get_project_description(working_directory, file_path="project_description.json"):
    """
    Reads a JSON file that describes the project structure, key files, and debugging notes.
    Returns the parsed description or a helpful error message.
    """
    target_file = os.path.join(working_directory, file_path)

    if not os.path.exists(target_file):
        return f"Error: Project description file '{file_path}' not found."

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        return f"Error reading project description: {e}"


schema_get_project_description = types.FunctionDeclaration(
    name="get_project_description",
    description="Fetch the project description or manifest to identify file responsibilities and debug notes.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="Relative path to the project description file.",
            )
        },
        required=[],
    ),
)
