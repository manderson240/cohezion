"""
Resource Guard - Protects the system from resource exhaustion during agentic tasks.
Enforces limits on CPU load and RAM usage.
"""

import asyncio
import logging
import os
import shutil
from dataclasses import dataclass

import psutil


logger = logging.getLogger(__name__)


@dataclass
class SystemVitals:
    cpu_load_1m: float
    ram_available_mb: int
    ram_percent: float
    swap_used_mb: int
    disk_free_gb: float
    disk_percent: float


class ResourceGuard:
    """
    Monitors system vitals and provides a 'throttle' for resource-intensive tasks.
    """

    def __init__(
        self,
        max_cpu_load: float = 24.0,
        min_ram_available_mb: int = 16384,  # 16GB
        max_ram_percent: float = 90.0,
        min_disk_free_gb: float = 20.0,  # 20GB for safe copy-on-write / snapshot operations
        max_disk_percent: float = 85.0,  # 85% max capacity limit to prevent ZFS fragmentation and read-only locks
    ) -> None:
        self.max_cpu_load = max_cpu_load
        self.min_ram_available_mb = min_ram_available_mb
        self.max_ram_percent = max_ram_percent
        self.min_disk_free_gb = min_disk_free_gb
        self.max_disk_percent = max_disk_percent

    def get_vitals(self) -> SystemVitals:
        """Get current system metrics."""
        load_avg = os.getloadavg()[0]  # 1-minute load average
        virtual_mem = psutil.virtual_memory()
        swap_mem = psutil.swap_memory()

        # Check workspace directory for disk usage
        try:
            from cohezion.config.unified import get_config

            path = str(get_config().root_dir)
        except Exception:
            path = os.getcwd()

        disk = shutil.disk_usage(path)
        disk_free = disk.free / (1024 * 1024 * 1024)  # convert to GB
        disk_percent = (disk.used / disk.total) * 100 if disk.total else 0.0

        return SystemVitals(
            cpu_load_1m=load_avg,
            ram_available_mb=virtual_mem.available // (1024 * 1024),
            ram_percent=virtual_mem.percent,
            swap_used_mb=swap_mem.used // (1024 * 1024),
            disk_free_gb=disk_free,
            disk_percent=disk_percent,
        )

    def is_healthy(self) -> tuple[bool, str]:
        """Check if system is healthy enough for extra load."""
        vitals = self.get_vitals()

        if vitals.cpu_load_1m > self.max_cpu_load:
            return False, f"CPU load too high: {vitals.cpu_load_1m}"

        if vitals.ram_available_mb < self.min_ram_available_mb:
            return False, f"RAM available too low: {vitals.ram_available_mb}MB"

        if vitals.ram_percent > self.max_ram_percent:
            return False, f"RAM usage too high: {vitals.ram_percent}%"

        if vitals.disk_free_gb < self.min_disk_free_gb:
            return (
                False,
                f"Disk space too low: {vitals.disk_free_gb:.2f}GB free (required: {self.min_disk_free_gb}GB)",
            )

        if vitals.disk_percent > self.max_disk_percent:
            return (
                False,
                f"Disk utilization too high: {vitals.disk_percent:.2f}% (max: {self.max_disk_percent}%)",
            )

        return True, "System healthy"

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
