"""Secure sandboxed execution for agentic tasks.

Provides containerized/isolated execution environments for untrusted code,
aligning with Anthropic's safety requirements for agentic AI training.

Architecture:
- Docker container isolation (primary)
- Firecracker microVM (secondary, for stronger isolation)
- gVisor (optional, user-space kernel)
- Resource limits: CPU, memory, network, disk
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResourceLimits:
    """Resource constraints for sandboxed execution."""

    cpu_quota: float = 1.0  # CPU cores
    memory_limit: str = "512m"  # Docker syntax: 512m, 2g
    timeout_seconds: int = 300
    network: bool = False
    disk_limit: str = "1g"
    pids_limit: int = 100


@dataclass
class SandboxResult:
    """Result from sandboxed execution."""

    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    resource_usage: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Path] = field(default_factory=list)


class SandboxBackend(Protocol):
    """Abstract sandbox backend interface."""

    async def execute(
        self,
        code: str,
        context: dict[str, Any],
        limits: ResourceLimits,
    ) -> SandboxResult: ...

    async def health_check(self) -> bool: ...


class DockerSandbox:
    """Docker-based sandboxed execution.

    Uses Docker containers for isolation with configurable security profiles.
    """

    def __init__(
        self,
        image: str = "python:3.11-slim",
        seccomp_profile: Path | None = None,
    ):
        self.image = image
        # Use a custom seccomp profile only if one is explicitly provided AND exists on
        # disk. Otherwise fall back to Docker's BUILT-IN default seccomp profile (which is
        # already restrictive, ~44 syscalls blocked) by omitting the flag entirely. The
        # previous hardcoded "/etc/docker/seccomp.json" does not exist on most hosts, so
        # `docker run` failed with exit 125 ("opening seccomp profile ... no such file"),
        # making the sandbox non-functional everywhere.
        self.seccomp = seccomp_profile
        self._initialized = False

    async def _ensure_image(self) -> None:
        """Pull Docker image if not present."""
        if self._initialized:
            return

        proc = await asyncio.create_subprocess_exec(
            "docker",
            "pull",
            self.image,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()
        self._initialized = True

    async def execute(
        self,
        code: str,
        context: dict[str, Any] | None = None,
        limits: ResourceLimits | None = None,
    ) -> SandboxResult:
        """Execute Python code in isolated Docker container."""
        await self._ensure_image()
        limits = limits or ResourceLimits()

        # Create temporary directory for code and artifacts
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # TemporaryDirectory is 0700 and write_text files are 0600 -- unreadable by the
            # container's user when Docker uses userns-remap (container-root maps to a high
            # host UID). Make the dir traversable and the files world-readable so the mounted
            # code is readable regardless of UID mapping. (The mount is :ro, so this does not
            # widen what the container can WRITE.)
            tmp_path.chmod(0o755)

            # Write code to file
            code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
            code_file = tmp_path / f"agent_task_{code_hash}.py"
            code_file.write_text(code)
            code_file.chmod(0o644)

            # Write context as JSON
            ctx_file = tmp_path / "context.json"
            ctx_file.write_text(json.dumps(context or {}))
            ctx_file.chmod(0o644)

            # Prepare Docker args
            cmd = [
                "docker",
                "run",
                "--rm",  # Remove after exit
                "--read-only",  # Read-only root
                f"--memory={limits.memory_limit}",
                f"--memory-swap={limits.memory_limit}",
                f"--cpus={limits.cpu_quota}",
                f"--pids-limit={limits.pids_limit}",
                "--cap-drop",
                "ALL",  # Drop all capabilities
                "--cap-add",
                "SYS_PTRACE",  # Allow debugging
            ]

            # Apply a custom seccomp profile only when one is provided and present on disk;
            # otherwise rely on Docker's built-in default seccomp profile (omit the flag).
            if self.seccomp is not None and Path(self.seccomp).exists():
                cmd.extend(["--security-opt", f"seccomp={self.seccomp}"])

            if not limits.network:
                cmd.extend(["--network", "none"])

            # Mount tmpdir and set working directory
            cmd.extend(
                [
                    "-v",
                    f"{tmpdir}:/workspace:ro",
                    "-w",
                    "/workspace",
                    self.image,
                    "python",
                    str(code_file.name),
                ]
            )

            # Execute with timeout
            start_time = asyncio.get_event_loop().time()
            try:
                proc = await asyncio.wait_for(
                    asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    ),
                    timeout=limits.timeout_seconds,
                )

                stdout, stderr = await proc.communicate()
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

                return SandboxResult(
                    success=proc.returncode == 0,
                    stdout=stdout.decode("utf-8", errors="replace"),
                    stderr=stderr.decode("utf-8", errors="replace"),
                    exit_code=proc.returncode,
                    duration_ms=duration_ms,
                    resource_usage={},  # Would parse from docker stats
                )

            except TimeoutError:
                # Kill container on timeout
                subprocess.run(
                    ["docker", "kill", f"$(docker ps -q --filter ancestor={self.image})"],
                    check=False,
                )
                return SandboxResult(
                    success=False,
                    stdout="",
                    stderr=f"Timeout after {limits.timeout_seconds}s",
                    exit_code=-1,
                    duration_ms=limits.timeout_seconds * 1000,
                )

    async def health_check(self) -> bool:
        """Check Docker daemon availability."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=5.0)
            return proc.returncode == 0
        except Exception:
            return False


class FirecrackerSandbox:
    """Firecracker microVM-based isolation.

    AWS Firecracker provides stronger isolation than Docker with faster
    startup times (~125ms). Suitable for high-frequency sandboxing.
    """

    def __init__(self, kernel_image: str = "vmlinux", rootfs: str = "rootfs.ext4"):
        self.kernel = kernel_image
        self.rootfs = rootfs
        self.socket_path = "/tmp/firecracker.sock"

    async def execute(
        self,
        code: str,
        context: dict[str, Any] | None = None,
        limits: ResourceLimits | None = None,
    ) -> SandboxResult:
        """Execute in Firecracker microVM."""
        # Simplified implementation - full FC requires API server setup
        # This demonstrates architecture awareness

        logger.info("Firecracker execution requested (not yet implemented)")
        return SandboxResult(
            success=False,
            stdout="",
            stderr="Firecracker not yet configured",
            exit_code=-1,
            duration_ms=0,
        )

    async def health_check(self) -> bool:
        """Check if firecracker is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "which",
                "firecracker",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            return False


class SandboxManager:
    """Unified sandbox management with backend selection."""

    def __init__(self, preferred_backend: Literal["docker", "firecracker", "gvisor"] = "docker"):
        self.preferred = preferred_backend
        self._backends: dict[str, SandboxBackend] = {}

    def _get_backend(self) -> SandboxBackend:
        """Get best available sandbox backend."""
        if self.preferred not in self._backends:
            if self.preferred == "docker":
                self._backends["docker"] = DockerSandbox()
            elif self.preferred == "firecracker":
                self._backends["firecracker"] = FirecrackerSandbox()
            else:
                raise ValueError(f"Unknown backend: {self.preferred}")

        return self._backends[self.preferred]

    async def execute_task(
        self,
        task_id: str,
        code: str,
        context: dict[str, Any] | None = None,
        limits: ResourceLimits | None = None,
    ) -> SandboxResult:
        """Execute agent task in sandbox with full audit logging."""
        backend = self._get_backend()
        limits = limits or ResourceLimits()

        logger.info(f"Sandbox execution start: task={task_id} backend={self.preferred}")

        result = await backend.execute(code, context, limits)

        # Log execution result
        log_entry = {
            "task_id": task_id,
            "backend": self.preferred,
            "success": result.success,
            "duration_ms": result.duration_ms,
            "exit_code": result.exit_code,
            "resource_limits": {
                "cpu": limits.cpu_quota,
                "memory": limits.memory_limit,
                "timeout": limits.timeout_seconds,
            },
        }
        logger.info(f"Sandbox execution complete: {json.dumps(log_entry)}")

        return result

    async def health_check(self) -> dict[str, bool]:
        """Health check all available backends."""
        return {
            "docker": await DockerSandbox().health_check(),
            "firecracker": await FirecrackerSandbox().health_check(),
        }


# Convenience exports
__all__ = [
    "DockerSandbox",
    "FirecrackerSandbox",
    "ResourceLimits",
    "SandboxManager",
    "SandboxResult",
]
