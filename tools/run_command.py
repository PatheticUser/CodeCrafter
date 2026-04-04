"""Tool: run_command — execute shell commands with safety blocklist."""

import re
import subprocess

from tools.base import BaseTool

# Dangerous command patterns — block to prevent destructive operations
_BLOCKED_PATTERNS = [
    r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?/",
    r"del\s+/[sS]\s+/[qQ]\s+[A-Za-z]:\\",
    r"rmdir\s+/[sS]\s+/[qQ]\s+[A-Za-z]:\\",
    r"format\s+[A-Za-z]:",
    r"mkfs\b",
    r"dd\s+if=",
    r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;",      # fork bomb
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
_BLOCKED_REGEX = [re.compile(p, re.IGNORECASE) for p in _BLOCKED_PATTERNS]


class RunCommandTool(BaseTool):
    name = "run_command"
    description = (
        "Execute a shell command in the working directory. "
        "Use for: installing packages (npm, pip), git operations, "
        "listing files, running build tools, or any terminal command. "
        "Returns stdout, stderr, and exit code."
    )
    parameters = {
        "command": {
            "type": "string",
            "description": "The shell command to execute (e.g., 'npm init -y', 'git status', 'ls -la')",
        },
        "timeout": {
            "type": "integer",
            "description": "Maximum seconds to wait for the command to finish. Default is 30.",
        },
    }
    required = ["command"]
    mutates_workspace = True
    auto_fixable = True

    def execute(self, *, command: str, timeout: int = 30, **_kw) -> str:
        if self._is_blocked(command):
            return "Error: This command has been blocked for safety reasons. It matches a dangerous pattern."

        try:
            result = subprocess.run(
                command, shell=True, cwd=self.working_directory,
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing command: {e}"

        parts: list[str] = []
        if result.stdout.strip():
            stdout = result.stdout.strip()
            if len(stdout) > 5000:
                stdout = stdout[:5000] + "\n...(truncated)"
            parts.append(f"STDOUT:\n{stdout}")
        if result.stderr.strip():
            stderr = result.stderr.strip()
            if len(stderr) > 2000:
                stderr = stderr[:2000] + "\n...(truncated)"
            parts.append(f"STDERR:\n{stderr}")

        parts.append(f"EXIT CODE: {result.returncode}")
        return "\n".join(parts) if parts else f"Command completed (exit code {result.returncode})"

    @staticmethod
    def _is_blocked(command: str) -> bool:
        return any(p.search(command) for p in _BLOCKED_REGEX)
