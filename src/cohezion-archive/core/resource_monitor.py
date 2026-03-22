"""
Resource Monitor Service.

Ensures Cohezion development (Agentic Work) always takes precedence over
background 'renting' tasks (Node Verification). Provides active defense against OOM.
"""

import logging
import os

import psutil


logger = logging.getLogger(__name__)


class ResourceMonitor:
    def __init__(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 90.0,
        log_interval: int = 5,
    ):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.log_interval = log_interval

    def get_stats(self) -> dict[str, float]:
        """Return current system stats."""
        vm = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": vm.percent,
            "available_memory_gb": vm.available / (1024**3),
            "used_memory_gb": vm.used / (1024**3),
            "total_memory_gb": vm.total / (1024**3),
        }

    def check_and_enforce(self) -> list[str]:
        """
        Active defense: Checks limits and potentially kills low-priority processes.
        Returns a list of actions taken.
        """
        stats = self.get_stats()
        actions = []

        if stats["memory_percent"] > self.memory_threshold:
            msg = f"⚠️ CRITICAL: Memory at {stats['memory_percent']}%! Engaging active defense."
            logger.warning(msg)
            actions.append(msg)

            # Find memory hogs
            # We specifically target 'git', 'python' (background workers), 'node'
            # But we must be careful not to kill specific PIDs (like ourselves)

            self_pid = os.getpid()

            for proc in psutil.process_iter(["pid", "name", "memory_percent", "cmdline"]):
                try:
                    # Don't kill ourselves or init
                    if proc.info["pid"] == self_pid or proc.info["pid"] < 100:
                        continue

                    # Target known background tasks if they are eating RAM
                    cmd = " ".join(proc.info["cmdline"] or []).lower()

                    # Heuristic targets
                    targets = [
                        "git diff",
                        "git status",
                        "pre-commit",
                        "npm run",
                        "node_modules",
                    ]

                    if any(t in cmd for t in targets) and proc.info["memory_percent"] > 5.0:
                        logger.warning(
                            f"Killing process {proc.info['pid']} ({proc.info['name']}) - {proc.info['memory_percent']:.1f}% MEM"
                        )
                        proc.kill()
                        actions.append(f"Killed {proc.info['name']} (PID {proc.info['pid']})")

                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    pass

        return actions

    def should_rent(self) -> bool:
        """
        Determine if resources are sufficient to run background 'renting' tasks.
        Returns True ONLY if system load is below thresholds.
        """
        stats = self.get_stats()

        cpu_ok = stats["cpu_percent"] < self.cpu_threshold
        mem_ok = stats["memory_percent"] < self.memory_threshold

        if not cpu_ok:
            logger.debug(f"Rent paused: High CPU ({stats['cpu_percent']}%)")

        if not mem_ok:
            logger.debug(f"Rent paused: High Memory ({stats['memory_percent']}%)")

        return cpu_ok and mem_ok


# Singleton
_INSTANCE = None


def get_resource_monitor() -> ResourceMonitor:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = ResourceMonitor()
    return _INSTANCE
