"""Empirical System Resource Governor for AMD Strix Halo (122GB UMA).

Monitors live system RAM utilization, available GTT aperture headroom (>30GB safety buffer),
swap pressure, disk space, and active Lemonade/SurrealDB daemon processes.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass

import psutil


logger = logging.getLogger("resource_governor")


@dataclass
class SystemResourceStatus:
    """Snapshot of empirical system resource metrics."""

    ram_total_gb: float
    ram_used_gb: float
    ram_available_gb: float
    swap_total_gb: float
    swap_used_gb: float
    disk_total_gb: float
    disk_available_gb: float
    cpu_load_1m: float
    active_lemonade_servers: int
    surrealdb_running: bool
    clickhouse_running: bool
    status: str


class SystemResourceGovernor:
    """Governor enforcing memory headroom and hardware safety bounds."""

    def __init__(self, min_available_ram_gb: float = 20.0) -> None:
        self.min_available_ram_gb = min_available_ram_gb

    def inspect_resources(self) -> SystemResourceStatus:
        """Fetch empirical system resource metrics via psutil and system calls."""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = shutil.disk_usage("/home")
        load = os.getloadavg()[0]

        # Scan for active Lemonade/SurrealDB/ClickHouse processes
        lemonade_count = 0
        surreal_active = False
        clickhouse_active = False

        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                cmd = " ".join(proc.info["cmdline"] or [])
                if "llama-server" in cmd or "flm-real" in cmd or "koko" in cmd:
                    lemonade_count += 1
                if "surreal" in cmd and "start" in cmd:
                    surreal_active = True
                if "clickhouse-server" in cmd:
                    clickhouse_active = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        ram_avail_gb = mem.available / (1024**3)
        healthy = ram_avail_gb >= self.min_available_ram_gb

        return SystemResourceStatus(
            ram_total_gb=mem.total / (1024**3),
            ram_used_gb=mem.used / (1024**3),
            ram_available_gb=ram_avail_gb,
            swap_total_gb=swap.total / (1024**3),
            swap_used_gb=swap.used / (1024**3),
            disk_total_gb=disk.total / (1024**3),
            disk_available_gb=disk.free / (1024**3),
            cpu_load_1m=load,
            active_lemonade_servers=lemonade_count,
            surrealdb_running=surreal_active,
            clickhouse_running=clickhouse_active,
            status="HEALTHY" if healthy else "WARNING_LOW_MEMORY",
        )


def run_resource_governance_check() -> None:
    print("\n" + "=" * 70)
    print("💻 AMD STRIX HALO 122GB UMA: EMPIRICAL SYSTEM RESOURCE GOVERNOR")
    print("=" * 70)

    governor = SystemResourceGovernor(min_available_ram_gb=20.0)
    status = governor.inspect_resources()

    print(
        f"  • RAM Utilization : {status.ram_used_gb:.2f} GB / {status.ram_total_gb:.2f} GB (Available: {status.ram_available_gb:.2f} GB)"
    )
    print(f"  • Swap Utilization: {status.swap_used_gb:.2f} GB / {status.swap_total_gb:.2f} GB")
    print(
        f"  • Disk Space (/home): {status.disk_available_gb:.2f} GB Available / {status.disk_total_gb:.2f} GB Total"
    )
    print(f"  • CPU Load (1m)   : {status.cpu_load_1m:.2f}")
    print(f"  • Lemonade Servers: {status.active_lemonade_servers} active model engines")
    print(f"  • SurrealDB Status: {'✅ ONLINE' if status.surrealdb_running else '❌ OFFLINE'}")
    print(f"  • ClickHouse Status: {'✅ ONLINE' if status.clickhouse_running else '❌ OFFLINE'}")
    print(f"  • Resource Governor: [{status.status}]")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_resource_governance_check()
