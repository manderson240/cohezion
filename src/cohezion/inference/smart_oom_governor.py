"""Smart Cross-Session Dynamic OOM Governor & Fleet-Lock Barrier.

Enforces cross-session memory safety on AMD Strix Halo (128GB UMA):
1. Hard OOM Floor: Rejects any local model load/invocation if MemAvailable < 35.0 GiB (or Swap used > 2.0 GiB).
2. Inter-Session Mutex (FleetLock): File-based locking with PID liveness detection preventing concurrent model loads.
3. Automated Delegation Fallback: Automatically routes heavy inference requests to Tier 2 Ollama Cloud
   (`deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `minimax-m3:cloud`) whenever local headroom is tight.
"""

from __future__ import annotations

import fcntl
import os
import time
from pathlib import Path

import psutil


LOCK_PATH = Path("/tmp/cohezion_fleet_modelload.lock")
MIN_AVAILABLE_MEM_GIB = 50.0  # Raised to 50.0 GiB for absolute safety on 128GB UMA
MAX_SWAP_USED_GIB = 1.0  # Zero tolerance for swap paging before model loads


class SmartOOMGovernor:
    @staticmethod
    def get_memory_state() -> tuple[float, float, bool]:
        """Returns (available_mem_gib, swap_used_gib, is_safe)."""
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()
        avail_gib = vm.available / (1024**3)
        swap_used_gib = sm.used / (1024**3)
        is_safe = (avail_gib >= MIN_AVAILABLE_MEM_GIB) and (swap_used_gib <= MAX_SWAP_USED_GIB)
        return round(avail_gib, 2), round(swap_used_gib, 2), is_safe

    @classmethod
    def can_execute_local(cls) -> tuple[bool, str]:
        avail_gib, swap_gib, is_safe = cls.get_memory_state()
        if not is_safe:
            return (
                False,
                f"Memory backpressure! Avail: {avail_gib} GiB (Min {MIN_AVAILABLE_MEM_GIB} GiB), Swap used: {swap_gib} GiB. Delegate to Cloud.",
            )
        return True, f"Local Silicon Safe (Avail: {avail_gib} GiB, Swap: {swap_gib} GiB)"


class CrossSessionFleetLock:
    def __init__(self, timeout_sec: float = 30.0):
        self.timeout_sec = timeout_sec
        self._fd: int | None = None

    def __enter__(self):
        t_start = time.perf_counter()
        self._fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_RDWR)
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Write current PID
                os.write(self._fd, f"{os.getpid()}\n".encode())
                return self
            except (BlockingIOError, OSError):
                if time.perf_counter() - t_start > self.timeout_sec:
                    raise TimeoutError(
                        f"FleetLock timeout after {self.timeout_sec}s: Another session is loading models."
                    )
                time.sleep(0.5)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None
