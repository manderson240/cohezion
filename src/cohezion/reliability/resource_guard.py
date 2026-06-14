"""
Resource Guard - Protects the system from resource exhaustion during agentic tasks.
Enforces limits on CPU load and RAM usage.
"""

import asyncio
import logging
import os
from dataclasses import dataclass

import psutil


logger = logging.getLogger(__name__)


@dataclass
class SystemVitals:
    cpu_load_1m: float
    ram_available_mb: int
    ram_percent: float
    swap_used_mb: int
    disk_free_gb: float = 0.0
    disk_percent: float = 0.0


class ResourceGuard:
    """
    Monitors system vitals and provides a 'throttle' for resource-intensive tasks.
    """

    def __init__(
        self,
        max_cpu_load: float = 24.0,
        min_ram_available_mb: int = 16384,  # 16GB
        max_ram_percent: float = 90.0,
        model_load_margin_mb: int = 2048,  # headroom kept free after a model load
        min_disk_free_gb: float = 1.0,
        max_disk_percent: float = 95.0,
    ) -> None:
        self.max_cpu_load = max_cpu_load
        self.min_ram_available_mb = min_ram_available_mb
        self.max_ram_percent = max_ram_percent
        self.model_load_margin_mb = model_load_margin_mb
        self.min_disk_free_gb = min_disk_free_gb
        self.max_disk_percent = max_disk_percent

    def get_vitals(self) -> SystemVitals:
        """Get current system metrics."""
        load_avg = os.getloadavg()[0]  # 1-minute load average
        virtual_mem = psutil.virtual_memory()
        swap_mem = psutil.swap_memory()

        disk = psutil.disk_usage("/")
        return SystemVitals(
            cpu_load_1m=load_avg,
            ram_available_mb=virtual_mem.available // (1024 * 1024),
            ram_percent=virtual_mem.percent,
            swap_used_mb=swap_mem.used // (1024 * 1024),
            disk_free_gb=disk.free / (1024**3),
            disk_percent=disk.percent,
        )

    def is_healthy(self) -> tuple[bool, str]:
        """Check if system is healthy enough for extra load."""
        vitals = self.get_vitals()

        if vitals.cpu_load_1m > self.max_cpu_load:
            return False, f"CPU load too high: {vitals.cpu_load_1m}"

        if vitals.disk_free_gb < self.min_disk_free_gb:
            return False, f"Disk space too low: {vitals.disk_free_gb:.2f}GB free"

        if vitals.disk_percent > self.max_disk_percent:
            return False, f"Disk utilization too high: {vitals.disk_percent}%"

        if vitals.ram_available_mb < self.min_ram_available_mb:
            return False, f"RAM available too low: {vitals.ram_available_mb}MB"

        if vitals.ram_percent > self.max_ram_percent:
            return False, f"RAM usage too high: {vitals.ram_percent}%"

        return True, "System healthy"

    def can_load_model(self, estimated_mb: int) -> tuple[bool, str]:
        """Hard OOM gate: can a model of ``estimated_mb`` be loaded in-process now?

        Enforces harness invariant K1 ("no models loaded without checking memory").
        Refuses when ``estimated_mb + model_load_margin_mb`` exceeds currently
        available RAM, so a load can never push the system into the OOM killer.

        An ``estimated_mb`` of 0 or less means "unknown size" and is allowed —
        the caller has explicitly opted out of an estimate (do not silently block).
        """
        if estimated_mb <= 0:
            return True, "no size estimate provided; gate skipped"

        available = self.get_vitals().ram_available_mb
        needed = estimated_mb + self.model_load_margin_mb
        if needed > available:
            return False, (
                f"OOM guard: model ~{estimated_mb}MB + {self.model_load_margin_mb}MB margin "
                f"= {needed}MB needed > {available}MB available RAM. Refusing in-process load — "
                f"route to an already-loaded lemonade node (HTTP) instead."
            )
        return True, f"fits: {needed}MB needed <= {available}MB available"

    def require_can_load(self, estimated_mb: int) -> None:
        """Raise ``MemoryError`` if a model of ``estimated_mb`` cannot be loaded.

        For call sites that must abort a load rather than branch on a bool.
        """
        ok, reason = self.can_load_model(estimated_mb)
        if not ok:
            raise MemoryError(reason)

    async def wait_for_stability(self, timeout_seconds: int = 300, check_interval: int = 5) -> bool:
        """Wait until system stabilizes or timeout occurs."""
        start_time = asyncio.get_event_loop().time()

        while True:
            healthy, reason = self.is_healthy()
            if healthy:
                return True

            if (asyncio.get_event_loop().time() - start_time) > timeout_seconds:
                logger.error(f"ResourceGuard timeout: {reason}")
                return False

            logger.warning(f"Throttling: {reason}. Waiting {check_interval}s...")
            await asyncio.sleep(check_interval)
