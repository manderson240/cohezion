r"""OOM Guard & Memory Headroom Safety Protocol
=============================================
Enforces memory safety rules for local silicon inference swarms on Framework 16 Strix Halo:
  1. Minimum Available Memory Floor: 20.0 GiB
  2. Sequential Single-Model Queue (`max_loaded_models: 1`)
  3. Inter-Agent Settle Pause: 3.0s
  4. Automatic Recovery Triggers (`scripts/recover_fleet.sh`)
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MemoryState:
    available_gb: float
    total_gb: float
    swap_used_gb: float
    is_safe: bool


class OOMGuard:
    """Memory guard to prevent kernel faults and Out-Of-Memory thrashing."""

    MIN_AVAILABLE_GB: float = 20.0

    @classmethod
    def get_memory_state(cls) -> MemoryState:
        """Inspect current system available memory via `free -m`."""
        try:
            out = subprocess.run(
                ["free", "-m"], capture_output=True, text=True, timeout=5
            ).stdout
            lines = out.strip().split("\n")
            mem_line = [x for x in lines if x.startswith("Mem:")][0].split()
            swap_line = [x for x in lines if x.startswith("Swap:")][0].split()

            total_mb = float(mem_line[1])
            available_mb = float(mem_line[6])
            swap_used_mb = float(swap_line[2])

            available_gb = available_mb / 1024.0
            total_gb = total_mb / 1024.0
            swap_used_gb = swap_used_mb / 1024.0

            is_safe = available_gb >= cls.MIN_AVAILABLE_GB

            return MemoryState(
                available_gb=round(available_gb, 2),
                total_gb=round(total_gb, 2),
                swap_used_gb=round(swap_used_gb, 2),
                is_safe=is_safe,
            )
        except Exception as e:
            logger.error(f"Failed to inspect memory state: {e}")
            return MemoryState(available_gb=0.0, total_gb=0.0, swap_used_gb=0.0, is_safe=False)

    @classmethod
    async def wait_for_headroom(cls, min_gb: float = 20.0, timeout: float = 120.0) -> bool:
        """Async wait until available memory rises above min_gb."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            state = cls.get_memory_state()
            if state.available_gb >= min_gb:
                logger.info(f"🟢 OOM Guard: {state.available_gb} GiB available (>= {min_gb} GiB floor)")
                return True
            logger.warning(
                f"⚠️ OOM Guard: Only {state.available_gb} GiB available (< {min_gb} GiB floor). Waiting..."
            )
            await asyncio.sleep(5.0)
        return False

    @classmethod
    def settle_pause(cls, seconds: float = 3.0) -> None:
        """Pause between inference tasks to let memory settle."""
        time.sleep(seconds)
