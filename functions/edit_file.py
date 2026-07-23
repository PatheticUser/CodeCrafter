import os

from functions._security import validate_path


def edit_file(working_directory, file_path, old_content, new_content):
    """
    Surgical file editing: finds exact `old_content` in the file and replaces it
    with `new_content`. Does NOT overwrite the entire file.

    Args:
        working_directory: The sandboxed working directory
        file_path: Relative path to the file to edit
        old_content: The exact text to find and replace
        new_content: The replacement text

    Returns:
        Success message or error with context to help the LLM self-correct
    """
    # Security: path traversal check
    err = validate_path(working_directory, file_path)
    if err:
        return err

    target_file_abs = os.path.realpath(os.path.join(working_directory, file_path))

    if not os.path.isfile(target_file_abs):
        return f'Error: File not found: "{file_path}"'

    # --- Read current content ---
    try:
        with open(target_file_abs, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"Error reading {file_path}: {e}"

    # --- Find and replace ---
    count = content.count(old_content)

    if count == 0:
        # Help the LLM self-correct by showing nearby content
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

    if count > 1:
        # Replace only the first occurrence and warn
        new_file_content = content.replace(old_content, new_content, 1)
        warning = f" (Warning: found {count} occurrences, replaced only the first one)"
    else:
        new_file_content = content.replace(old_content, new_content)
        warning = ""

    # --- Write back ---
    try:
        with open(target_file_abs, "w", encoding="utf-8") as f:
            f.write(new_file_content)

        # Calculate what changed
        old_lines = old_content.count("\n") + 1
        new_lines = new_content.count("\n") + 1
        return f'Successfully edited "{file_path}" — replaced {old_lines} line(s) with {new_lines} line(s){warning}'

    except Exception as e:
        return f"Error writing {file_path}: {e}"


# --- OpenAI-compatible tool schema ---
schema_edit_file = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": (
            "Make a surgical edit to an existing file by finding and replacing specific content. "
            "Use this instead of write_file when you only need to change part of a file. "
            "Provide the exact text to find (old_content) and its replacement (new_content). "
            "If the old_content is not found, an error with a file preview is returned to help you correct your edit."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The relative path of the file to edit.",
                },
                "old_content": {
                    "type": "string",
                    "description": "The exact text currently in the file that you want to replace. Must match exactly including whitespace and indentation.",
                },
                "new_content": {
                    "type": "string",
                    "description": "The new text to replace old_content with.",
                },
            },
            "required": ["file_path", "old_content", "new_content"],
        },
    },
}
