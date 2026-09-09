"""System-Wide Inter-Process Hardware FleetLock & Dynamic OOM Eviction Governor.

Enforces cross-session, multi-agent hardware locking across all running Python/Shell processes
on AMD Strix Halo to prevent concurrent GPU/NPU aperture allocation races and system OOM.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from cohezion.reliability.oom_guard import OOMGuard

logger = logging.getLogger(__name__)

LOCK_FILE_DIR = Path("/tmp/cohezion/locks")
LOCK_FILE_DIR.mkdir(parents=True, exist_ok=True)


class SystemWideFleetLock:
    """Inter-process file-descriptor lock utilizing kernel-level fcntl.flock."""

    def __init__(self, resource_name: str = "modelload"):
        self.resource_name = resource_name
        self.lock_path = LOCK_FILE_DIR / f"{resource_name}.lock"
        self._fd: int | None = None

    def acquire(self, timeout: float = 30.0, poll_interval: float = 0.2) -> bool:
        """Attempt to acquire exclusive system-wide lock across all OS processes."""
        t_start = time.perf_counter()
        # Open WITHOUT O_TRUNC to avoid clobbering incumbent lock owner metadata
        self._fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR, 0o666)

        while (time.perf_counter() - t_start) < timeout:
            # First check OOM headroom
            mem = OOMGuard.get_memory_state()
            if not mem.is_safe:
                logger.warning(
                    f"⚠️ SystemWideFleetLock: Available memory ({mem.available_gb} GiB) is below dynamic floor ({mem.dynamic_floor_gb} GiB). Waiting..."
                )
                time.sleep(poll_interval * 2)
                continue

            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Truncate and write owner metadata only AFTER lock is held
                os.ftruncate(self._fd, 0)
                os.lseek(self._fd, 0, os.SEEK_SET)
                os.write(
                    self._fd,
                    json.dumps({
                        "pid": os.getpid(),
                        "acquired_at": time.time(),
                        "resource": self.resource_name
                    }).encode("utf-8")
                )
                return True
            except (BlockingIOError, OSError):
                time.sleep(poll_interval)

        logger.error(f"❌ SystemWideFleetLock timed out after {timeout}s waiting on {self.resource_name}")
        # Cleanly close fd on timeout to prevent fd leaks
        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None
        return False

    def release(self) -> None:
        """Release the system-wide fcntl lock."""
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None

    @contextmanager
    def hold(self, timeout: float = 30.0) -> Generator[bool, None, None]:
        acquired = self.acquire(timeout=timeout)
        try:
            yield acquired
        finally:
            if acquired:
                self.release()
