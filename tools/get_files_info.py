"""Tool: get_files_info — recursively list workspace files."""

import os
from datetime import datetime

from tools.base import BaseTool


class GetFilesInfoTool(BaseTool):
    name = "get_files_info"
    description = (
        "Recursively lists files in the specified directory (relative to the working directory). "
        "Includes file size and modified date (without reading file content). "
        "Ensures directory stays within the working directory."
    )
    parameters = {
        "directory": {
            "type": "string",
            "description": (
                "The directory to list files from, relative to the working directory. "
                "If not provided, lists files in the working directory itself."
            ),
        },
    }
    required = []

    def execute(self, *, directory: str = ".", **_kw) -> str | list[dict]:
        abs_dir, err = self.dir_must_exist(directory)
        if err:
            # If directory doesn't exist, check the raw validate_path error first
            abs_dir2, err2 = self.validate_path(directory)
            if err2:
                return err2
            if not os.path.exists(abs_dir2):
                return f'Error: "{directory}" does not exist'
            if not os.path.isdir(abs_dir2):
                return f'Error: "{directory}" is not a directory'
            return err

        files_info: list[dict] = []
        for root, _, files in os.walk(abs_dir):
            for fname in files:
                file_path = os.path.join(root, fname)
                relative_path = os.path.relpath(file_path, self.working_directory)
                try:
                    stats = os.stat(file_path)
                    files_info.append({
                        "path": relative_path,
                        "size_kb": round(stats.st_size / 1024, 2),
                        "modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    })
                except Exception:
                    continue  # Skip unreadable files

        return files_info
