"""Docker-based Sandbox for Cohezion Agents.

Provides a secure, isolated environment for executing agent-generated code,
critical for the Anthropic 'Universes' role alignment.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import tarfile
import time
from dataclasses import dataclass
from typing import Any

import docker


logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """The result of a sandboxed execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    output_files: dict[str, bytes] = None


class ContainerizedUniverse:
    """A hardened containerized environment for agentic tasks."""

    def __init__(
        self,
        image_name: str = "python:3.11-slim",
        memory_limit: str = "512m",
        cpu_quota: int = 50000,  # 50% of one core
        timeout_seconds: int = 300,
        network_mode: str = "bridge",
        profile: Any | None = None,
    ):
        # If a SandboxProfile is provided, use it to override defaults.
        # Duck-type check avoids isinstance() issues when the class is mocked in tests.
        if profile is not None and hasattr(profile, "to_docker_memory_str"):
            memory_limit = profile.to_docker_memory_str()
            cpu_quota = profile.cpu_quota_percent * 1000
            timeout_seconds = profile.timeout_seconds
            network_mode = "bridge" if profile.network_enabled else "none"

        self.image_name = image_name
        self.memory_limit = memory_limit
        self.cpu_quota = cpu_quota
        self.timeout_seconds = timeout_seconds
        self.network_mode = network_mode

        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise RuntimeError("Docker is required for ContainerizedUniverse") from e

    async def execute_code(
        self,
        script_content: str,
        files: dict[str, str | bytes] | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute Python code within a sandboxed container."""
        return await asyncio.to_thread(self._sync_execute, script_content, files, env)

    def _sync_execute(
        self,
        script_content: str,
        files: dict[str, str | bytes] | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Synchronous wrapper for container execution."""
        start_time = time.time()
        container = None
        try:
            # 1. Prepare Docker image
            self._prepare_container()

            # 2. Create container
            run_kwargs: dict[str, Any] = {
                "command": "python main.py",
                "mem_limit": self.memory_limit,
                "cpu_quota": self.cpu_quota,
                "environment": env or {},
                "working_dir": "/app",
            }
            if self.network_mode != "bridge":
                run_kwargs["network_mode"] = self.network_mode
            container = self.client.containers.create(self.image_name, **run_kwargs)

            # 3. Create a tar archive of the code and files
            tar_stream = self._create_tar_stream(script_content, files)

            # 4. Put the archive into the container BEFORE starting
            container.put_archive("/app", tar_stream)

            # 5. Start the container (script is already injected)
            container.start()

            # 6. Wait for execution
            result = container.wait(timeout=self.timeout_seconds)

            # 7. Capture logs
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8")

            # 8. Extract output files from /app/output
            output_files = self._extract_output_files(container)

            duration = time.time() - start_time
            exit_code = result.get("StatusCode", -1)

            return SandboxResult(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                output_files=output_files,
            )

        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return SandboxResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration=time.time() - start_time,
            )
        finally:
            if container:
                with contextlib.suppress(Exception):
                    container.remove(force=True)

    def _create_tar_stream(self, script: str, files: dict[str, str | bytes] | None) -> bytes:
        """Create a tar archive in memory."""
        import io

        file_obj = io.BytesIO()
        with tarfile.open(fileobj=file_obj, mode="w") as tar:
            # Add main script
            script_bytes = script.encode("utf-8")
            tarinfo = tarfile.TarInfo("main.py")
            tarinfo.size = len(script_bytes)
            tar.addfile(tarinfo, io.BytesIO(script_bytes))

            # Add other files
            if files:
                for name, content in files.items():
                    content_bytes = content.encode("utf-8") if isinstance(content, str) else content
                    tarinfo = tarfile.TarInfo(name)
                    tarinfo.size = len(content_bytes)
                    tar.addfile(tarinfo, io.BytesIO(content_bytes))

        file_obj.seek(0)
        return file_obj.read()

    def _extract_output_files(self, container: Any) -> dict[str, bytes] | None:
        """Extract files from /app/output in the container."""
        import io

        try:
            archive_stream, _stat = container.get_archive("/app/output")
            archive_bytes = b"".join(archive_stream)
            output_files: dict[str, bytes] = {}
            with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r") as tar:
                for member in tar.getmembers():
                    if member.isfile():
                        extracted = tar.extractfile(member)
                        if extracted is not None:
                            # Strip the leading "output/" prefix
                            name = member.name
                            if "/" in name:
                                name = name.split("/", 1)[1]
                            output_files[name] = extracted.read()
            return output_files if output_files else None
        except Exception:
            # No output directory or extraction failed — not an error
            return None

    def _prepare_container(self):
        """Ensure the required image is pulled."""
        try:
            self.client.images.get(self.image_name)
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling image {self.image_name}...")
            self.client.images.pull(self.image_name)
