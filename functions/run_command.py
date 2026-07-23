import subprocess
import re
import os


# Dangerous command patterns — block these to prevent destructive operations
# and path traversal outside the workspace
BLOCKED_PATTERNS = [
    # Filesystem destruction
    r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?/",  # rm -rf / or rm /
    r"del\s+/[sS]\s+/[qQ]\s+[A-Za-z]:\\",  # del /s /q C:\
    r"rmdir\s+/[sS]\s+/[qQ]\s+[A-Za-z]:\\",  # rmdir /s /q C:\
    r"format\s+[A-Za-z]:",  # format C:
    r"mkfs\b",  # mkfs
    r"dd\s+if=",  # dd if=
    r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;",  # fork bomb
    # Data exfiltration
    r"curl\s+.*-d\s+@",  # curl posting file data
    r"wget\s+.*--post-file",  # wget posting files
    # System manipulation
    r"shutdown\b",  # shutdown
    r"reboot\b",  # reboot
    r"reg\s+(delete|add)\s+HKLM",  # Windows registry manipulation
    r"chmod\s+777\s+/",  # chmod 777 on root
    r"chown\s+.*\s+/",  # chown on root paths
    # Credential/key theft
    r"cat\s+.*(\.ssh|\.gnupg|credentials|shadow|passwd)",
    r"type\s+.*\\(\.ssh|credentials)",
    # Path traversal — reading/writing outside working directory via ..
    r"(?:^|[;&|])\s*cd\s+\.\.",  # cd .. to escape
    r"(?:^|[;&|])\s*pushd\s+\.\.",  # pushd .. to escape
]

BLOCKED_REGEX = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]


def _is_command_blocked(command):
    """Check if a command matches any blocked pattern."""
    for pattern in BLOCKED_REGEX:
        if pattern.search(command):
            return True
    return False


def run_command(working_directory, command, timeout=30):
    """
    Executes a shell command in the working directory.

    Args:
        working_directory: The working directory to run the command in
        command: The shell command to execute
        timeout: Maximum seconds to wait (default 30)

    Returns:
        String with stdout, stderr, and exit code
    """
    # Security: validate working directory exists and is accessible
    if not working_directory:
        return "Error: Working directory is not set"
    wd_abs = os.path.realpath(working_directory)
    if not os.path.isdir(wd_abs):
        return f'Error: Working directory does not exist: "{working_directory}"'

    # Security: block dangerous commands
    if _is_command_blocked(command):
        return "Error: This command has been blocked for safety reasons. It matches a dangerous pattern."

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=wd_abs,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output_parts = []
        if result.stdout.strip():
            stdout = result.stdout.strip()
            if len(stdout) > 5000:
                stdout = stdout[:5000] + "\n...(truncated)"
            output_parts.append(f"STDOUT:\n{stdout}")
        if result.stderr.strip():
            stderr = result.stderr.strip()
            if len(stderr) > 2000:
                stderr = stderr[:2000] + "\n...(truncated)"
            output_parts.append(f"STDERR:\n{stderr}")

        output_parts.append(f"EXIT CODE: {result.returncode}")

        return (
            "\n".join(output_parts)
            if output_parts
            else f"Command completed (exit code {result.returncode})"
        )

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {e}"


# --- OpenAI-compatible tool schema for Groq ---
schema_run_command = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": (
            "Executes a shell command in the working directory. "
            "Use for: installing packages (npm, pip), git operations, "
            "listing files, running build tools, or any terminal command. "
            "Returns stdout, stderr, and exit code."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute (e.g., 'npm init -y', 'git status', 'ls -la')",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum seconds to wait for the command to finish. Default is 30.",
                },
            },
            "required": ["command"],
        },
    },
}
