"""Tool: delete_file — safely remove a file from the workspace."""

import os

from tools.base import BaseTool


class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Delete a file safely within the working directory."
    parameters = {
        "file_path": {
            "type": "string",
            "description": "Relative path of the file to delete.",
        },
    }
    required = ["file_path"]
    mutates_workspace = True

    def execute(self, *, file_path: str, **_kw) -> str:
        abs_path, err = self.validate_path(file_path)
        if err:
            return err

        if not os.path.exists(abs_path):
            return f'Error: File "{file_path}" not found.'

        if not os.path.isfile(abs_path):
            return f'Error: "{file_path}" is not a file and cannot be deleted.'

        try:
            os.remove(abs_path)
            return f'Successfully deleted "{file_path}".'
        except PermissionError:
            return f'Error: Permission denied while deleting "{file_path}".'
        except Exception as e:
            return f'Error deleting "{file_path}": {e}'
