"""Tool: edit_file — surgical find-and-replace editing."""

from tools.base import BaseTool


class EditFileTool(BaseTool):
    name = "edit_file"
    description = (
        "Make a surgical edit to an existing file by finding and replacing specific content. "
        "Use this instead of write_file when you only need to change part of a file. "
        "Provide the exact text to find (old_content) and its replacement (new_content). "
        "If the old_content is not found, an error with a file preview is returned."
    )
    parameters = {
        "file_path": {
            "type": "string",
            "description": "Relative path of the file to edit.",
        },
        "old_content": {
            "type": "string",
            "description": (
                "The exact text currently in the file that you want to replace. "
                "Must match exactly including whitespace and indentation."
            ),
        },
        "new_content": {
            "type": "string",
            "description": "The new text to replace old_content with.",
        },
    }
    required = ["file_path", "old_content", "new_content"]
    mutates_workspace = True

    def execute(self, *, file_path: str, old_content: str, new_content: str, **_kw) -> str:
        abs_path, err = self.file_must_exist(file_path)
        if err:
            return err

        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return f"Error reading {file_path}: {e}"

        count = content.count(old_content)

        if count == 0:
            return self._not_found_error(file_path, content)

        if count > 1:
            new_file_content = content.replace(old_content, new_content, 1)
            warning = f" (Warning: found {count} occurrences, replaced only the first one)"
        else:
            new_file_content = content.replace(old_content, new_content)
            warning = ""

        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(new_file_content)
            old_lines = old_content.count("\n") + 1
            new_lines = new_content.count("\n") + 1
            return (
                f'Successfully edited "{file_path}" — '
                f"replaced {old_lines} line(s) with {new_lines} line(s){warning}"
            )
        except Exception as e:
            return f"Error writing {file_path}: {e}"

    @staticmethod
    def _not_found_error(file_path: str, content: str) -> str:
        """Help the LLM self-correct by showing nearby content."""
        lines = content.split("\n")
        total = len(lines)
        if total <= 30:
            preview = content
        else:
            preview = (
                "\n".join(lines[:15])
                + f"\n\n... ({total - 25} lines omitted) ...\n\n"
                + "\n".join(lines[-10:])
            )
        return (
            f'Error: Could not find the specified old_content in "{file_path}". '
            f"The file has {total} lines. Here is a preview of the actual content:\n\n"
            f"```\n{preview}\n```\n\n"
            f"Please use get_file_content or get_file_outline to see the exact content before editing."
        )
