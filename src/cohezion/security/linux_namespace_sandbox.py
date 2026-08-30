"""Linux Namespaces & Bubblewrap (bwrap) Micro-Sandbox for Cohezion.

Provides zero-root, unprivileged kernel isolation across:
1. Mount Namespace (CLONE_NEWNS) -> Isolated read-only filesystem root + ephemeral tmpfs.
2. PID Namespace (CLONE_NEWPID) -> Dedicated PID tree; cannot inspect or signal host processes.
3. Network Namespace (CLONE_NEWNET) -> Loopback-only network isolation (zero internet egress).
4. IPC Namespace (CLONE_NEWIPC) -> Isolated POSIX message queues & shared memory.
5. UTS Namespace (CLONE_NEWUTS) -> Isolated hostname.
6. User Namespace (CLONE_NEWUSER) -> Mapped unprivileged UID/GID without root privileges.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("cohezion.sandbox.namespaces")
_BWRAP = shutil.which("bwrap") or "/usr/bin/bwrap"


@dataclass(frozen=True, slots=True)
class NamespaceExecutionResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    namespace_pid: int | None = None
    network_isolated: bool = True
    filesystem_isolated: bool = True


class LinuxNamespaceSandbox:
    """Unprivileged Linux Namespace Sandbox using Bubblewrap (bwrap)."""

    def __init__(self, timeout_sec: float = 10.0, allow_network: bool = False):
        self.timeout_sec = timeout_sec
        self.allow_network = allow_network
        self.bwrap_path = _BWRAP
        self.is_available = os.path.exists(self.bwrap_path) and os.access(self.bwrap_path, os.X_OK)

    def execute_python_code(
        self,
        code: str,
        workspace_dir: str | None = None,
        timeout: float | None = None,
    ) -> NamespaceExecutionResult:
        """Execute arbitrary untrusted Python code in full Linux namespaces."""
        if not self.is_available:
            raise RuntimeError(f"Bubblewrap binary not found at {self.bwrap_path}")

        timeout_val = timeout or self.timeout_sec
        t0 = time.perf_counter()

        with tempfile.TemporaryDirectory(prefix="cohezion_ns_") as tmp_dir:
            script_path = os.path.join(tmp_dir, "payload.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Build bwrap arguments for full unprivileged namespace isolation
            bwrap_cmd = [
                self.bwrap_path,
                "--ro-bind", "/usr", "/usr",
                "--ro-bind", "/lib", "/lib",
                "--proc", "/proc",
                "--dev-bind", "/dev/null", "/dev/null",
                "--dev-bind", "/dev/zero", "/dev/zero",
                "--dev-bind", "/dev/urandom", "/dev/urandom",
                "--tmpfs", "/tmp",
                "--tmpfs", "/dev/shm",
                "--dir", "/workspace",
                "--bind", tmp_dir, "/workspace",
                "--chdir", "/workspace",
                "--die-with-parent",
                "--as-pid-1",
                "--unshare-all",
                "--uid", str(os.getuid()),
                "--gid", str(os.getgid()),
            ]

            if os.path.exists("/lib64"):
                bwrap_cmd.extend(["--ro-bind", "/lib64", "/lib64"])
            if os.path.exists("/bin") and not os.path.islink("/bin"):
                bwrap_cmd.extend(["--ro-bind", "/bin", "/bin"])
            if os.path.exists("/etc"):
                bwrap_cmd.extend(["--ro-bind", "/etc", "/etc"])

            # If workspace directory provided, mount read-only
            if workspace_dir and os.path.exists(workspace_dir):
                bwrap_cmd.extend(["--ro-bind", workspace_dir, "/ro_workspace"])

            # Command to run inside the namespace
            bwrap_cmd.extend(["python3", "/workspace/payload.py"])

            # Wrap in systemd-run cgroups v2 if available to prevent 273 GB/s allocation races
            systemd_run = shutil.which("systemd-run")
            if systemd_run and os.path.exists("/sys/fs/cgroup"):
                cmd = [
                    systemd_run,
                    "--user",
                    "--scope",
                    "-q",
                    "-p", "MemoryMax=4G",
                    "-p", "MemoryHigh=3.5G",
                    "-p", "TasksMax=64",
                    "--",
                ] + bwrap_cmd
            else:
                cmd = bwrap_cmd

            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_val,
                )
                dt_ms = (time.perf_counter() - t0) * 1000.0
                return NamespaceExecutionResult(
                    success=(proc.returncode == 0),
                    exit_code=proc.returncode,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    duration_ms=round(dt_ms, 3),
                    network_isolated=not self.allow_network,
                    filesystem_isolated=True,
                )
            except subprocess.TimeoutExpired as exc:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                return NamespaceExecutionResult(
                    success=False,
                    exit_code=-1,
                    stdout=exc.stdout or "",
                    stderr=f"Namespace execution timed out after {timeout_val}s",
                    duration_ms=round(dt_ms, 3),
                    network_isolated=not self.allow_network,
                    filesystem_isolated=True,
                )
            except Exception as exc:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                return NamespaceExecutionResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Namespace execution failure: {type(exc).__name__}: {exc}",
                    duration_ms=round(dt_ms, 3),
                    network_isolated=not self.allow_network,
                    filesystem_isolated=True,
                )
