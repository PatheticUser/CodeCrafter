import subprocess
import re


BLOCKED_PATTERNS = [
    r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?/",
    r"del\s+/[sS]\s+/[qQ]\s+[A-Za-z]:\\",
    r"rmdir\s+/[sS]\s+/[qQ]\s+[A-Za-z]:\\",
    r"format\s+[A-Za-z]:",
    r"mkfs\b",
    r"dd\s+if=",
    r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;",
    r"curl\s+.*-d\s+@",
    r"wget\s+.*--post-file",
    r"shutdown\b",
    r"reboot\b",
    r"reg\s+(delete|add)\s+HKLM",
    r"chmod\s+777\s+/",
    r"chown\s+.*\s+/",
    r"cat\s+.*(\.ssh|\.gnupg|credentials|shadow|passwd)",
    r"type\s+.*\\(\.ssh|credentials)",
]

BLOCKED_REGEX = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]


def _is_command_blocked(command):
    for pattern in BLOCKED_REGEX:
        if pattern.search(command):
            return True
    return False


def run_command(working_directory, command, timeout=30):
    """
    Executes a shell command in the working directory.
    """
    if _is_command_blocked(command):
        return "Error: This command has been blocked for safety reasons. It matches a dangerous pattern."

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=working_directory,
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
                    "description": "The shell command to execute.",
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
