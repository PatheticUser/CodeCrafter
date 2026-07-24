"""Shared security utilities for workspace confinement.
All tool functions should use these validators instead of duplicating the path traversal check.
Uses realpath to prevent symlink-escape attacks.
"""

import os


def validate_path(working_directory: str, target_path: str) -> str | None:
    """Validate that *target_path* (relative) is confined within *working_directory*.

    Resolves symlinks via ``realpath`` to prevent symlink-based escapes.
    Returns ``None`` if the path is safe, otherwise an error message string.
    """
    working_dir_abs = os.path.realpath(working_directory)
    target_abs = os.path.realpath(os.path.join(working_directory, target_path))
    if not (target_abs == working_dir_abs or target_abs.startswith(working_dir_abs + os.sep)):
        return (
            f"Error: Cannot access \"{target_path}\" — outside the permitted working directory"
        )
    return None


def validate_directory(working_directory: str, target_dir: str) -> str | None:
    """Validate that *target_dir* is a real directory confined within *working_directory*.

    Returns ``None`` if valid, otherwise an error message.
    """
    err = validate_path(working_directory, target_dir)
    if err:
        return err
    target_abs = os.path.realpath(os.path.join(working_directory, target_dir))
    if not os.path.isdir(target_abs):
        return f"Error: Directory not found: \"{target_dir}\""
    return None


def validate_working_directory(working_directory: str) -> str | None:
    """Validate that the working directory itself is set and exists.

    Returns ``None`` if valid, otherwise an error message.
    """
    if not working_directory:
        return "Error: Working directory is not set"
    wd_abs = os.path.realpath(working_directory)
    if not os.path.isdir(wd_abs):
        return f"Error: Working directory does not exist: \"{working_directory}\""
    return None
