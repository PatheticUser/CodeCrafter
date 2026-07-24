import difflib
import os

from src.tools._security import validate_path


def _compute_diff(old_text: str, new_text: str, context_lines: int = 2) -> str:
    """Compute a compact unified diff between old and new text."""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diff = difflib.unified_diff(
        old_lines, new_lines,
        n=context_lines,
        lineterm="",
    )
    lines = []
    for line in diff:
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            continue
        lines.append(line)
    return "\n".join(lines)


def edit_file(working_directory, file_path, old_content, new_content):
    """
    Surgical file editing: finds exact `old_content` in the file and replaces it
    with `new_content`. Does NOT overwrite the entire file.
    Returns dict with 'result' and 'diff' on success.
    """
    err = validate_path(working_directory, file_path)
    if err:
        return err

    target_file_abs = os.path.realpath(os.path.join(working_directory, file_path))

    if not os.path.isfile(target_file_abs):
        return f'Error: File not found: "{file_path}"'

    try:
        with open(target_file_abs, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"Error reading {file_path}: {e}"

    count = content.count(old_content)

    if count == 0:
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
        new_file_content = content.replace(old_content, new_content, 1)
        warning = f" (Warning: found {count} occurrences, replaced only the first one)"
    else:
        new_file_content = content.replace(old_content, new_content)
        warning = ""

    # Compute diff before writing
    diff_text = _compute_diff(content, new_file_content)

    try:
        with open(target_file_abs, "w", encoding="utf-8") as f:
            f.write(new_file_content)

        old_lines = old_content.count("\n") + 1
        new_lines = new_content.count("\n") + 1
        result = f'Successfully edited "{file_path}" \u2014 replaced {old_lines} line(s) with {new_lines} line(s){warning}'
        return {"result": result, "diff": diff_text}

    except Exception as e:
        return f"Error writing {file_path}: {e}"


schema_edit_file = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Search+replace within a file. Use for targeted edits. Shows file preview on mismatch.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "File path relative to workspace.",
                },
                "old_content": {
                    "type": "string",
                    "description": "Exact text to find (whitespace-sensitive).",
                },
                "new_content": {
                    "type": "string",
                    "description": "Replacement text.",
                },
            },
            "required": ["file_path", "old_content", "new_content"],
        },
    },
}
