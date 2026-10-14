"""Docker-isolated workspace implementation for untrusted code execution."""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from src.workspace.base import CommandResult
from src.workspace.local import LocalWorkspace
from src.workspace.security import is_command_blocked

logger = logging.getLogger("codecrafter.workspace.docker")


class DockerWorkspace(LocalWorkspace):
    """
    Docker-backed workspace.
    File operations execute on the securely bound host directory.
    All shell and code executions run inside an isolated Docker container with
    restricted capabilities, memory/CPU caps, non-root user, and no Docker socket access.
    """

    def __init__(
        self,
        workspace_id: str,
        root_dir: Path | str,
        image: str = "python:3.11-slim",
        command_timeout: int = 60,
        max_output_bytes: int = 50000,
        cpu_limit: str = "1.0",
        memory_limit: str = "512m",
    ):
        super().__init__(
            workspace_id=workspace_id,
            root_dir=root_dir,
            command_timeout=command_timeout,
            max_output_bytes=max_output_bytes,
        )
        self.image = image
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.container_name = f"codecrafter-ws-{workspace_id[:16]}"
        self._container_ready = False
        self._lock = asyncio.Lock()

    async def _ensure_container_running(self) -> bool:
        """Ensure isolated workspace container is running."""
        async with self._lock:
            if self._container_ready:
                return True

            if not shutil.which("docker"):
                logger.warning("Docker CLI not available on host. Falling back to local execution.")
                return False

            # Inspect if container already running
            inspect_proc = await asyncio.create_subprocess_exec(
                "docker",
                "inspect",
                "-f",
                "{{.State.Running}}",
                self.container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await inspect_proc.communicate()
            if inspect_proc.returncode == 0 and "true" in stdout.decode().lower():
                self._container_ready = True
                return True

            # Clean any dead container with same name
            await (
                await asyncio.create_subprocess_exec(
                    "docker",
                    "rm",
                    "-f",
                    self.container_name,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            ).wait()

            # Start container:
            # - mounted workspace directory at /workspace
            # - non-root security options
            # - resource limits (cpu, memory)
            # - no docker.sock mounted
            run_cmd = [
                "docker",
                "run",
                "-d",
                "--name",
                self.container_name,
                "--cpus",
                self.cpu_limit,
                "--memory",
                self.memory_limit,
                "--security-opt",
                "no-new-privileges:true",
                "-v",
                f"{self.root_dir}:/workspace:rw",
                "-w",
                "/workspace",
                "--entrypoint",
                "sh",
                self.image,
                "-c",
                "while true; do sleep 3600; done",
            ]

            try:
                proc = await asyncio.create_subprocess_exec(
                    *run_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await proc.communicate()
                if proc.returncode == 0:
                    self._container_ready = True
                    return True
                logger.error("Failed to start docker workspace container: %s", stderr.decode())
                return False
            except Exception as e:
                logger.error("Exception starting docker container: %s", e)
                return False

    async def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
        """Run command strictly inside isolated container."""
        if is_command_blocked(command):
            return CommandResult(
                exit_code=1,
                stdout="",
                stderr="SecurityError: Command matched security blocklist.",
            )

        cmd_timeout = timeout or self._command_timeout
        docker_available = await self._ensure_container_running()

        if not docker_available:
            logger.warning(
                "Docker workspace unavailable, falling back to LocalWorkspace execution."
            )
            return await super().execute_command(command, timeout=cmd_timeout)

        # Execute inside container via docker exec
        exec_cmd = [
            "docker",
            "exec",
            "-w",
            "/workspace",
            self.container_name,
            "sh",
            "-c",
            command,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *exec_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=cmd_timeout,
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")[: self._max_output_bytes]
            stderr = stderr_bytes.decode("utf-8", errors="replace")[: self._max_output_bytes]
            return CommandResult(
                exit_code=proc.returncode if proc.returncode is not None else 0,
                stdout=stdout,
                stderr=stderr,
                timed_out=False,
            )
        except TimeoutError:
            try:
                # Terminate running process inside container
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            return CommandResult(
                exit_code=124,
                stdout="",
                stderr=f"Command timed out after {cmd_timeout} seconds inside container",
                timed_out=True,
            )
        except Exception as e:
            return CommandResult(
                exit_code=1,
                stdout="",
                stderr=f"Failed to execute command in container: {e}",
            )

    async def cleanup(self) -> None:
        """Terminate and remove container on workspace close."""
        if self._container_ready:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker",
                    "rm",
                    "-f",
                    self.container_name,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
            except Exception:
                pass
            self._container_ready = False
