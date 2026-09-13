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
    # Optional (default 0.0) so pre-shmem constructors (tests, callers on
    # main's API shape) still build; get_memory_state() always sets it from
    # /proc/meminfo when available.
    shmem_gb: float = 0.0
    dynamic_floor_gb: float = 20.0
    gtt_used_gb: float = 0.0
    gtt_total_gb: float = 0.0
    psi_some_10: float = 0.0

    @property
    def used_gb(self) -> float:
        """Estimate used memory in GiB (total_gb - available_gb)."""
        return max(0.0, self.total_gb - self.available_gb)


class OOMGuard:
    """Memory guard to prevent kernel faults and Out-Of-Memory thrashing."""

    DEFAULT_MIN_AVAILABLE_GB: float = 20.0
    MIN_AVAILABLE_GB: float = 20.0
    MAX_SAFE_GTT_GB: float = 50.0
    MAX_SAFE_SWAP_USED_GB: float = 12.0
    MAX_SAFE_PSI: float = 20.0

    @classmethod
    def calculate_dynamic_floor(
        cls, largest_model_gb: float = 16.0, shmem_gb: float = 0.0
    ) -> float:
        """Compute dynamic memory floor: base 10GB + largest resident model + shmem overhead."""
        return max(cls.DEFAULT_MIN_AVAILABLE_GB, 10.0 + largest_model_gb + (shmem_gb * 1.5))

    @classmethod
    def get_memory_state(cls, largest_model_gb: float = 16.0) -> MemoryState:
        """Inspect system available memory, /proc/meminfo Shmem, GTT aperture, and PSI pressure."""
        try:
            # 1. Inspect free -m
            out = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5).stdout
            lines = out.strip().split("\n")
            mem_line = next(x for x in lines if x.startswith("Mem:")).split()
            swap_line = next(x for x in lines if x.startswith("Swap:")).split()

            total_mb = float(mem_line[1])
            available_mb = float(mem_line[6])
            swap_used_mb = float(swap_line[2])

            available_gb = available_mb / 1024.0
            total_gb = total_mb / 1024.0
            swap_used_gb = swap_used_mb / 1024.0

            # 2. Inspect /proc/meminfo for Shmem / IPC allocations
            shmem_gb = 0.0
            try:
                with open("/proc/meminfo", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("Shmem:"):
                            shmem_kb = float(line.split()[1])
                            shmem_gb = shmem_kb / (1024.0 * 1024.0)
                            break
            except Exception:
                pass

            # 3. Inspect GTT aperture from AMD GPU sysfs (Strix Halo / UMA)
            gtt_used_gb = 0.0
            gtt_total_gb = 0.0
            import glob

            for p_used in glob.glob("/sys/class/drm/card*/device/mem_info_gtt_used"):
                try:
                    with open(p_used, "r", encoding="utf-8") as f:
                        gtt_used_gb = max(gtt_used_gb, float(f.read().strip()) / (1024.0**3))
                except Exception:
                    pass
            for p_total in glob.glob("/sys/class/drm/card*/device/mem_info_gtt_total"):
                try:
                    with open(p_total, "r", encoding="utf-8") as f:
                        gtt_total_gb = max(gtt_total_gb, float(f.read().strip()) / (1024.0**3))
                except Exception:
                    pass

            # 4. Inspect kernel Memory PSI (Pressure Stall Information)
            psi_some_10 = 0.0
            try:
                with open("/proc/pressure/memory", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("some"):
                            for token in line.split():
                                if token.startswith("avg10="):
                                    psi_some_10 = float(token.split("=")[1])
                                    break
                            break
            except Exception:
                pass

            dynamic_floor = cls.calculate_dynamic_floor(largest_model_gb, shmem_gb)
            is_safe = (
                available_gb >= dynamic_floor
                and gtt_used_gb <= cls.MAX_SAFE_GTT_GB
                and swap_used_gb <= cls.MAX_SAFE_SWAP_USED_GB
                and psi_some_10 <= cls.MAX_SAFE_PSI
            )

            return MemoryState(
                available_gb=round(available_gb, 2),
                total_gb=round(total_gb, 2),
                swap_used_gb=round(swap_used_gb, 2),
                shmem_gb=round(shmem_gb, 2),
                is_safe=is_safe,
                dynamic_floor_gb=round(dynamic_floor, 2),
                gtt_used_gb=round(gtt_used_gb, 2),
                gtt_total_gb=round(gtt_total_gb, 2),
                psi_some_10=round(psi_some_10, 2),
            )
        except Exception as e:
            logger.error(f"Failed to inspect memory state: {e}")
            return MemoryState(
                available_gb=0.0,
                total_gb=0.0,
                swap_used_gb=0.0,
                shmem_gb=0.0,
                is_safe=False,
                dynamic_floor_gb=cls.DEFAULT_MIN_AVAILABLE_GB,
                gtt_used_gb=0.0,
                gtt_total_gb=0.0,
                psi_some_10=0.0,
            )

    @classmethod
    async def wait_for_headroom(cls, min_gb: float = 20.0, timeout: float = 120.0) -> bool:
        """Async wait until available memory rises above min_gb."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            state = cls.get_memory_state()
            if state.available_gb >= min_gb:
                logger.info(
                    f"🟢 OOM Guard: {state.available_gb} GiB available (>= {min_gb} GiB floor)"
                )
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
