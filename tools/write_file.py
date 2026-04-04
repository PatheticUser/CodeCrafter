"""Tool: write_file — create a new file in the workspace."""

from tools.base import BaseTool


class WriteFileTool(BaseTool):
    name = "write_file"
    description = (
        "Create a new file (or overwrite an existing one) with the provided content. "
        "Creates any missing parent directories automatically. "
        "Returns a success or error message."
    )
    parameters = {
        "file_path": {
            "type": "string",
            "description": "Relative path of the file to create inside the working directory.",
        },
        "content": {
            "type": "string",
            "description": "The content to write into the file.",
        },
    }
    required = ["file_path", "content"]
    mutates_workspace = True

    def execute(self, *, file_path: str, content: str, **_kw) -> str:
        import os

        abs_path, err = self.validate_path(file_path)
        if err:
            return err

        # Ensure parent directories exist
        parent = os.path.dirname(abs_path)
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception as e:
            return f"Error: Failed to create directories for {file_path}: {e}"

        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'
        except Exception as e:
            return f"Error: Failed to write to {file_path}: {e}"
