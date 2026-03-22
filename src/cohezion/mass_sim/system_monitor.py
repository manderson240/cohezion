"""System resource monitor for OOM protection during mass simulation.

Monitors RSS, swap, CPU temperature to prevent system instability.
Adaptive batch sizing: reduces batch_size when memory pressure detected.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass


logger = logging.getLogger(__name__)

# Memory thresholds in GB
WARN_THRESHOLD_GB = 90.0  # Start warning
THROTTLE_THRESHOLD_GB = 100.0  # Reduce batch size
ABORT_THRESHOLD_GB = 115.0  # Stop simulation gracefully


@dataclass
class SystemVitals:
    """Snapshot of system resource usage."""

    rss_gb: float  # Process resident set size
    total_ram_gb: float
    available_ram_gb: float
    swap_used_gb: float
    cpu_percent: float
    timestamp: float


def get_vitals() -> SystemVitals:
    """Read system vitals from /proc without psutil dependency."""
    rss_gb = 0.0
    total_ram_gb = 128.0
    available_ram_gb = 64.0
    swap_used_gb = 0.0
    cpu_percent = 0.0

    # Process RSS from /proc/self/status
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    rss_kb = int(line.split()[1])
                    rss_gb = rss_kb / (1024 * 1024)
                    break
    except (OSError, ValueError):
        pass

    # System memory from /proc/meminfo
    try:
        with open("/proc/meminfo") as f:
            meminfo = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    meminfo[parts[0].rstrip(":")] = int(parts[1])
            total_ram_gb = meminfo.get("MemTotal", 0) / (1024 * 1024)
            available_ram_gb = meminfo.get("MemAvailable", 0) / (1024 * 1024)
            swap_total = meminfo.get("SwapTotal", 0)
            swap_free = meminfo.get("SwapFree", 0)
            swap_used_gb = (swap_total - swap_free) / (1024 * 1024)
    except (OSError, ValueError):
        pass

    # CPU from /proc/loadavg (1-minute load / n_cpus)
    try:
        with open("/proc/loadavg") as f:
            load_1m = float(f.read().split()[0])
            n_cpus = os.cpu_count() or 32
            cpu_percent = min(100.0, (load_1m / n_cpus) * 100.0)
    except (OSError, ValueError):
        pass

    return SystemVitals(
        rss_gb=rss_gb,
        total_ram_gb=total_ram_gb,
        available_ram_gb=available_ram_gb,
        swap_used_gb=swap_used_gb,
        cpu_percent=cpu_percent,
        timestamp=time.time(),
    )


class MemoryGuard:
    """Adaptive memory guard that throttles batch sizes to prevent OOM.

    Usage:
        guard = MemoryGuard(max_memory_gb=100.0)
        batch_size = guard.safe_batch_size(requested=2000, z_dim=256)
        if guard.should_abort():
            break
    """

    def __init__(self, max_memory_gb: float = 100.0):
        self.max_memory_gb = max_memory_gb
        self._last_check = 0.0
        self._cached_vitals: SystemVitals | None = None
        self._check_interval = 5.0  # Seconds between checks

    def vitals(self) -> SystemVitals:
        """Get vitals with caching to avoid /proc spam."""
        now = time.time()
        if now - self._last_check > self._check_interval:
            self._cached_vitals = get_vitals()
            self._last_check = now
        return self._cached_vitals or get_vitals()

    def safe_batch_size(self, requested: int, z_dim: int = 256) -> int:
        """Compute OOM-safe batch size, scaling down under memory pressure."""
        v = self.vitals()

        if v.available_ram_gb < 10.0:
            # Critical: minimal batches
            safe = max(10, requested // 10)
            logger.warning(f"CRITICAL memory: {v.available_ram_gb:.1f}GB free, batch {requested}->{safe}")
            return safe

        if v.rss_gb > THROTTLE_THRESHOLD_GB or v.available_ram_gb < 20.0:
            # Throttle: halve batch size
            safe = max(50, requested // 2)
            logger.warning(
                f"Memory pressure: RSS={v.rss_gb:.1f}GB, avail={v.available_ram_gb:.1f}GB, batch {requested}->{safe}"
            )
            return safe

        if v.rss_gb > WARN_THRESHOLD_GB:
            logger.info(f"Memory watch: RSS={v.rss_gb:.1f}GB, avail={v.available_ram_gb:.1f}GB")

        return requested

    def should_abort(self) -> bool:
        """Return True if memory situation is dangerous."""
        v = self.vitals()
        if v.rss_gb > ABORT_THRESHOLD_GB:
            logger.error(f"ABORT: RSS={v.rss_gb:.1f}GB exceeds {ABORT_THRESHOLD_GB}GB limit")
            return True
        if v.available_ram_gb < 5.0:
            logger.error(f"ABORT: Only {v.available_ram_gb:.1f}GB available RAM")
            return True
        if v.swap_used_gb > 20.0:
            logger.error(f"ABORT: Swap usage {v.swap_used_gb:.1f}GB indicates thrashing")
            return True
        return False

    def log_status(self, prefix: str = "") -> None:
        """Log current memory status."""
        v = self.vitals()
        logger.info(
            f"{prefix}Memory: RSS={v.rss_gb:.1f}GB, "
            f"avail={v.available_ram_gb:.1f}GB, "
            f"swap={v.swap_used_gb:.1f}GB, "
            f"cpu={v.cpu_percent:.0f}%"
        )
