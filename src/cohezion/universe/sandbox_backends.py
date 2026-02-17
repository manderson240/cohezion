"""Isolation backends for sandboxed simulation execution.

Provides a Protocol-based abstraction over three isolation strategies:
- DockerBackend: Strongest isolation via ContainerizedUniverse (requires Docker).
- SystemdRunBackend: Native cgroups via systemd-run (Linux, near-zero overhead).
- SubprocessBackend: resource.setrlimit-based limits (always available, weakest).

Use ``select_backend()`` to auto-select the strongest available backend.
"""

from __future__ import annotations

import asyncio
import logging
import os
import resource
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable


if TYPE_CHECKING:
    from cohezion.universe.sandbox_profiles import SandboxProfile


logger = logging.getLogger(__name__)


@dataclass
class BackendResult:
    """Result from an isolation backend execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    output_files: dict[str, bytes] | None = None


@runtime_checkable
class IsolationBackend(Protocol):
    """Protocol for sandbox isolation backends.

    Mirrors the EncoderProtocol pattern from engine.py.
    """

    async def execute(
        self,
        script_content: str,
        profile: SandboxProfile,
        files: dict[str, str | bytes] | None = None,
        env: dict[str, str] | None = None,
    ) -> BackendResult:
        """Execute a script within the isolation boundary."""
        ...

    async def cleanup(self) -> None:
        """Release any held resources."""
        ...

    @classmethod
    def is_available(cls) -> bool:
        """Check whether this backend is usable on the current system."""
        ...


class DockerBackend:
    """Docker-based isolation using ContainerizedUniverse."""

    def __init__(self, image_name: str = "python:3.11-slim"):
        self.image_name = image_name

    async def execute(
        self,
        script_content: str,
        profile: SandboxProfile,
        files: dict[str, str | bytes] | None = None,
        env: dict[str, str] | None = None,
    ) -> BackendResult:
        """Execute script in a Docker container with profile constraints."""
        from cohezion.universe.sandbox import ContainerizedUniverse

        sandbox = ContainerizedUniverse(
            image_name=self.image_name,
            memory_limit=profile.to_docker_memory_str(),
            cpu_quota=profile.cpu_quota_percent * 1000,
            timeout_seconds=profile.timeout_seconds,
            network_mode="bridge" if profile.network_enabled else "none",
        )
        result = await sandbox.execute_code(script_content, files=files, env=env)
        return BackendResult(
            success=result.success,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=result.duration,
            output_files=result.output_files,
        )

    async def cleanup(self) -> None:
        """No persistent state to clean up."""

    @classmethod
    def is_available(cls) -> bool:
        """Check if Docker daemon is reachable."""
        try:
            import docker

            client = docker.from_env()
            client.ping()
            return True
        except Exception as e:
            logger.debug("Docker daemon not reachable: %s", e)
            return False


class SystemdRunBackend:
    """systemd-run based isolation using native cgroups.

    Uses ``systemd-run --scope`` with MemoryMax and CPUQuota properties.
    Near-zero overhead compared to Docker, but Linux-only and requires
    systemd (available on most modern Linux distros).
    """

    async def execute(
        self,
        script_content: str,
        profile: SandboxProfile,
        files: dict[str, str | bytes] | None = None,
        env: dict[str, str] | None = None,
    ) -> BackendResult:
        """Execute script under systemd-run scope with cgroup limits."""
        start_time = time.time()
        workdir = Path(tempfile.mkdtemp(prefix="cohezion_systemd_"))

        try:
            # Write script and files to workdir
            script_path = workdir / "main.py"
            script_path.write_text(script_content)

            if files:
                for name, content in files.items():
                    fpath = workdir / name
                    fpath.parent.mkdir(parents=True, exist_ok=True)
                    if isinstance(content, str):
                        fpath.write_text(content)
                    else:
                        fpath.write_bytes(content)

            # Build systemd-run command
            props = profile.to_systemd_args()
            cmd = ["systemd-run", "--scope", "--user"]
            for prop in props:
                cmd.extend(["-p", prop])
            cmd.extend(["python3", str(script_path)])

            # Build environment
            run_env = os.environ.copy()
            if env:
                run_env.update(env)

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workdir),
                env=run_env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=profile.timeout_seconds)
            except TimeoutError:
                proc.kill()
                await proc.wait()
                return BackendResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Timeout after {profile.timeout_seconds}s",
                    duration=time.time() - start_time,
                )

            output_files = _collect_output_files(workdir)

            return BackendResult(
                success=proc.returncode == 0,
                exit_code=proc.returncode or 0,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                duration=time.time() - start_time,
                output_files=output_files,
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    async def cleanup(self) -> None:
        """No persistent state to clean up."""

    @classmethod
    def is_available(cls) -> bool:
        """Check if systemd-run is available and functional."""
        if shutil.which("systemd-run") is None:
            return False
        try:
            result = subprocess.run(
                ["systemd-run", "--scope", "--user", "true"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False


class SubprocessBackend:
    """Subprocess-based isolation using resource.setrlimit.

    Weakest isolation but always available. Uses Python's resource module
    to set RLIMIT_AS (address space) and RLIMIT_CPU limits on the child process.
    """

    async def execute(
        self,
        script_content: str,
        profile: SandboxProfile,
        files: dict[str, str | bytes] | None = None,
        env: dict[str, str] | None = None,
    ) -> BackendResult:
        """Execute script in a subprocess with rlimit constraints."""
        start_time = time.time()
        workdir = Path(tempfile.mkdtemp(prefix="cohezion_subprocess_"))

        try:
            # Write script and files to workdir
            script_path = workdir / "main.py"
            script_path.write_text(script_content)

            if files:
                for name, content in files.items():
                    fpath = workdir / name
                    fpath.parent.mkdir(parents=True, exist_ok=True)
                    if isinstance(content, str):
                        fpath.write_text(content)
                    else:
                        fpath.write_bytes(content)

            # Compute rlimits
            memory_bytes = profile.memory_limit_mb * 1024 * 1024
            cpu_seconds = profile.timeout_seconds

            def set_limits() -> None:
                """preexec_fn to apply rlimits in the child process."""
                resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))

            # Build environment
            run_env = os.environ.copy()
            if env:
                run_env.update(env)

            result = await asyncio.to_thread(
                self._run_sync,
                script_path=script_path,
                workdir=workdir,
                set_limits=set_limits,
                timeout=profile.timeout_seconds,
                env=run_env,
            )

            output_files = _collect_output_files(workdir)

            return BackendResult(
                success=result["success"],
                exit_code=result["exit_code"],
                stdout=result["stdout"],
                stderr=result["stderr"],
                duration=time.time() - start_time,
                output_files=output_files,
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    @staticmethod
    def _run_sync(
        script_path: Path,
        workdir: Path,
        set_limits: Any,
        timeout: int,
        env: dict[str, str],
    ) -> dict[str, Any]:
        """Synchronous subprocess execution with rlimits."""
        try:
            result = subprocess.run(
                ["python3", str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(workdir),
                preexec_fn=set_limits,
                env=env,
            )
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Timeout after {timeout}s",
            }

    async def cleanup(self) -> None:
        """No persistent state to clean up."""

    @classmethod
    def is_available(cls) -> bool:
        """Subprocess backend is always available."""
        return True


def _collect_output_files(workdir: Path) -> dict[str, bytes] | None:
    """Scan {workdir}/output/ for files and return them as a dict.

    Returns
    -------
    dict[str, bytes] | None
        Mapping of filename to file content, or None if no output files exist.
    """
    output_dir = workdir / "output"
    if not output_dir.is_dir():
        return None

    output_files: dict[str, bytes] = {}
    for fpath in output_dir.iterdir():
        if fpath.is_file():
            output_files[fpath.name] = fpath.read_bytes()

    return output_files if output_files else None


def select_backend() -> IsolationBackend:
    """Auto-select the strongest available isolation backend.

    Preference order: Docker > systemd-run > subprocess.

    Returns
    -------
    IsolationBackend
        The strongest available backend instance.
    """
    if DockerBackend.is_available():
        logger.info("Selected Docker isolation backend")
        return DockerBackend()

    if SystemdRunBackend.is_available():
        logger.info("Selected systemd-run isolation backend")
        return SystemdRunBackend()

    logger.info("Selected subprocess isolation backend (weakest)")
    return SubprocessBackend()
