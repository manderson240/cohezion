"""
Resource Monitor for Simulations
================================

Monitors CPU, memory, disk, and network usage during simulations.
Provides alerts when resources exceed thresholds.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psutil


logger = logging.getLogger("ResourceMonitor")


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources at a point in time."""

    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    io_read_mb: float
    io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_percent": round(self.memory_percent, 2),
            "memory_used_gb": round(self.memory_used_gb, 2),
            "memory_available_gb": round(self.memory_available_gb, 2),
            "disk_percent": round(self.disk_percent, 2),
            "disk_used_gb": round(self.disk_used_gb, 2),
            "disk_free_gb": round(self.disk_free_gb, 2),
            "io_read_mb": round(self.io_read_mb, 2),
            "io_write_mb": round(self.io_write_mb, 2),
            "network_sent_mb": round(self.network_sent_mb, 2),
            "network_recv_mb": round(self.network_recv_mb, 2),
        }


@dataclass
class ResourceThresholds:
    """Thresholds for resource alerts."""

    cpu_warning: float = 80.0
    cpu_critical: float = 95.0
    memory_warning: float = 80.0
    memory_critical: float = 95.0
    disk_warning: float = 85.0
    disk_critical: float = 95.0


class ResourceMonitor:
    """Monitor system resources during simulations."""

    def __init__(
        self,
        thresholds: ResourceThresholds | None = None,
        check_interval_seconds: float = 5.0,
        history_size: int = 1000,
    ):
        self.thresholds = thresholds or ResourceThresholds()
        self.check_interval = check_interval_seconds
        self.history: list[ResourceSnapshot] = []
        self.history_size = history_size
        self._running = False
        self._disk_path = Path("/home/mike-anderson/nvme-simulations")

        # Initial IO counters
        self._io_start = psutil.disk_io_counters()
        self._net_start = psutil.net_io_counters()
        self._start_time = time.time()

    def capture(self) -> ResourceSnapshot:
        """Capture current resource snapshot."""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Memory
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024**3)
        memory_available_gb = memory.available / (1024**3)

        # Disk
        disk = psutil.disk_usage(str(self._disk_path))
        disk_used_gb = disk.used / (1024**3)
        disk_free_gb = disk.free / (1024**3)

        # IO (since start)
        io_now = psutil.disk_io_counters()
        io_read_mb = (io_now.read_bytes - self._io_start.read_bytes) / (1024**2)
        io_write_mb = (io_now.write_bytes - self._io_start.write_bytes) / (1024**2)

        # Network (since start)
        net_now = psutil.net_io_counters()
        network_sent_mb = (net_now.bytes_sent - self._net_start.bytes_sent) / (1024**2)
        network_recv_mb = (net_now.bytes_recv - self._net_start.bytes_recv) / (1024**2)

        snapshot = ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_gb=memory_used_gb,
            memory_available_gb=memory_available_gb,
            disk_percent=disk.percent,
            disk_used_gb=disk_used_gb,
            disk_free_gb=disk_free_gb,
            io_read_mb=io_read_mb,
            io_write_mb=io_write_mb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
        )

        # Add to history
        self.history.append(snapshot)
        if len(self.history) > self.history_size:
            self.history.pop(0)

        return snapshot

    def check_thresholds(self, snapshot: ResourceSnapshot) -> list[dict]:
        """Check if any thresholds are exceeded and return alerts."""
        alerts = []

        # CPU
        if snapshot.cpu_percent > self.thresholds.cpu_critical:
            alerts.append(
                {
                    "level": "CRITICAL",
                    "resource": "CPU",
                    "value": snapshot.cpu_percent,
                    "threshold": self.thresholds.cpu_critical,
                    "message": f"CPU usage critical: {snapshot.cpu_percent:.1f}%",
                }
            )
        elif snapshot.cpu_percent > self.thresholds.cpu_warning:
            alerts.append(
                {
                    "level": "WARNING",
                    "resource": "CPU",
                    "value": snapshot.cpu_percent,
                    "threshold": self.thresholds.cpu_warning,
                    "message": f"CPU usage high: {snapshot.cpu_percent:.1f}%",
                }
            )

        # Memory
        if snapshot.memory_percent > self.thresholds.memory_critical:
            alerts.append(
                {
                    "level": "CRITICAL",
                    "resource": "Memory",
                    "value": snapshot.memory_percent,
                    "threshold": self.thresholds.memory_critical,
                    "message": f"Memory usage critical: {snapshot.memory_percent:.1f}%",
                }
            )
        elif snapshot.memory_percent > self.thresholds.memory_warning:
            alerts.append(
                {
                    "level": "WARNING",
                    "resource": "Memory",
                    "value": snapshot.memory_percent,
                    "threshold": self.thresholds.memory_warning,
                    "message": f"Memory usage high: {snapshot.memory_percent:.1f}%",
                }
            )

        # Disk
        if snapshot.disk_percent > self.thresholds.disk_critical:
            alerts.append(
                {
                    "level": "CRITICAL",
                    "resource": "Disk",
                    "value": snapshot.disk_percent,
                    "threshold": self.thresholds.disk_critical,
                    "message": f"Disk usage critical: {snapshot.disk_percent:.1f}%",
                }
            )
        elif snapshot.disk_percent > self.thresholds.disk_warning:
            alerts.append(
                {
                    "level": "WARNING",
                    "resource": "Disk",
                    "value": snapshot.disk_percent,
                    "threshold": self.thresholds.disk_warning,
                    "message": f"Disk usage high: {snapshot.disk_percent:.1f}%",
                }
            )

        return alerts

    def get_summary(self) -> dict:
        """Get summary statistics from history."""
        if not self.history:
            return {}

        cpu_values = [s.cpu_percent for s in self.history]
        memory_values = [s.memory_percent for s in self.history]

        return {
            "duration_seconds": time.time() - self._start_time,
            "samples": len(self.history),
            "cpu": {
                "avg": round(sum(cpu_values) / len(cpu_values), 2),
                "max": round(max(cpu_values), 2),
                "min": round(min(cpu_values), 2),
            },
            "memory": {
                "avg": round(sum(memory_values) / len(memory_values), 2),
                "max": round(max(memory_values), 2),
                "min": round(min(memory_values), 2),
            },
            "current": self.history[-1].to_dict(),
        }

    def save_history(self, path: Path) -> None:
        """Save resource history to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "start_time": datetime.fromtimestamp(self._start_time).isoformat(),
            "end_time": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "snapshots": [s.to_dict() for s in self.history],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"💾 Resource history saved: {path}")


# Global monitor instance
_global_monitor: ResourceMonitor | None = None


def get_resource_monitor(
    thresholds: ResourceThresholds | None = None, check_interval_seconds: float = 5.0
) -> ResourceMonitor:
    """Get or create global resource monitor."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = ResourceMonitor(thresholds, check_interval_seconds)
    return _global_monitor


def reset_resource_monitor() -> None:
    """Reset global resource monitor."""
    global _global_monitor
    _global_monitor = None


if __name__ == "__main__":
    # Test resource monitor
    print("🖥️  Testing Resource Monitor...")

    monitor = ResourceMonitor(check_interval_seconds=1.0)

    # Capture a few snapshots
    for i in range(3):
        snapshot = monitor.capture()
        print(f"\nSnapshot {i + 1}:")
        print(f"  CPU: {snapshot.cpu_percent:.1f}%")
        print(
            f"  Memory: {snapshot.memory_percent:.1f}% ({snapshot.memory_used_gb:.1f} GB used)"
        )
        print(
            f"  Disk: {snapshot.disk_percent:.1f}% ({snapshot.disk_free_gb:.1f} GB free)"
        )

        alerts = monitor.check_thresholds(snapshot)
        if alerts:
            print(f"  ⚠️  Alerts: {len(alerts)}")
            for alert in alerts:
                print(f"     - {alert['level']}: {alert['message']}")
        else:
            print("  ✅ All resources within thresholds")

        time.sleep(1)

    # Show summary
    print("\n📊 Summary:")
    summary = monitor.get_summary()
    print(f"  Duration: {summary['duration_seconds']:.1f}s")
    print(f"  Samples: {summary['samples']}")
    print(f"  CPU avg/max: {summary['cpu']['avg']}% / {summary['cpu']['max']}%")
    print(
        f"  Memory avg/max: {summary['memory']['avg']}% / {summary['memory']['max']}%"
    )

    # Save history
    monitor.save_history(Path("/tmp/resource_test.json"))
    print("\n✅ Resource monitor test complete")
