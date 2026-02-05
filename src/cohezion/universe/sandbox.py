"""Docker-based Sandbox for Cohezion Agents.

Provides a secure, isolated environment for executing agent-generated code,
critical for the Anthropic 'Universes' role alignment.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tarfile
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException

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
    ):
        self.image_name = image_name
        self.memory_limit = memory_limit
        self.cpu_quota = cpu_quota
        self.timeout_seconds = timeout_seconds
        
        try:
            self.client = docker.from_env()
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise RuntimeError("Docker is required for ContainerizedUniverse") from e

    async def execute_code(
        self, 
        script_content: str, 
        files: dict[str, str | bytes] | None = None,
        env: dict[str, str] | None = None
    ) -> SandboxResult:
        """Execute Python code within a sandboxed container."""
        return await asyncio.to_thread(self._sync_execute, script_content, files, env)

    def _sync_execute(
        self, 
        script_content: str, 
        files: dict[str, str | bytes] | None = None,
        env: dict[str, str] | None = None
    ) -> SandboxResult:
        """Synchronous wrapper for container execution."""
        start_time = time.time()
        container = None
        try:
            # 1. Prepare Docker image
            self._prepare_container()

            # 2. Create container
            container = self.client.containers.run(
                self.image_name,
                command="python main.py",
                mem_limit=self.memory_limit,
                cpu_quota=self.cpu_quota,
                environment=env or {},
                detach=True,
                remove=False, # We'll remove it manually after getting logs
                working_dir="/app"
            )

            # 3. Create a tar archive of the code and files
            tar_stream = self._create_tar_stream(script_content, files)
            
            # 4. Put the archive into the container
            container.put_archive("/app", tar_stream)

            # 5. Wait for execution
            result = container.wait(timeout=self.timeout_seconds)
            
            # 6. Capture logs
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8")
            
            # 7. Extract output files (if any created in /app/output)
            # This is a bit complex for a skeleton, so we'll skip for now
            # but in production we'd use: container.get_archive("/app/output")

            duration = time.time() - start_time
            exit_code = result.get("StatusCode", -1)

            return SandboxResult(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration=duration
            )

        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return SandboxResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration=time.time() - start_time
            )
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

    def _create_tar_stream(self, script: str, files: dict[str, str | bytes] | None) -> bytes:
        """Create a tar archive in memory."""
        import io
        import tarfile
        
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
                    if isinstance(content, str):
                        content_bytes = content.encode("utf-8")
                    else:
                        content_bytes = content
                    tarinfo = tarfile.TarInfo(name)
                    tarinfo.size = len(content_bytes)
                    tar.addfile(tarinfo, io.BytesIO(content_bytes))
                    
        file_obj.seek(0)
        return file_obj.read()

    def _prepare_container(self):
        """Ensure the required image is pulled."""
        try:
            self.client.images.get(self.image_name)
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling image {self.image_name}...")
            self.client.images.pull(self.image_name)
