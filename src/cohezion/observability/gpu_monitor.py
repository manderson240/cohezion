"""GPU monitoring and thermal profiling for AMD Radeon integrated GPU.

Collects GPU utilization, memory usage, temperature, and power metrics
to profile token efficiency across different batch sizes and concurrency limits.

Metrics:
- GPU load: 0-100%
- VRAM usage: MB
- GTT (system memory) usage: MB
- Temperature: °C
- Throttle status: thermal/power/none
- Sclk/Mclk: GPU/memory clock frequency

Usage::

    monitor = GPUMonitor()
    monitor.start_measurement()

    # Run batch processing...
    results = await token_client.batch_generate(items)

    metrics = monitor.stop_measurement()
    print(f"GPU Load: {metrics['avg_gpu_load']}%")
    print(f"Throughput: {metrics['tokens_per_second']} tok/sec")
"""

from __future__ import annotations

import logging
import re
import statistics
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class GPUMetrics:
    """Single GPU measurement snapshot."""

    timestamp: float
    gpu_load: float  # 0-100%
    gpu_mem_used: float  # MB
    gtt_mem_used: float  # MB
    sclk: float  # GPU clock MHz
    mclk: float  # Memory clock MHz
    temperature: float  # °C
    throttle_status: str  # "thermal", "power", "none"


@dataclass
class ThermalProfilingResult:
    """Complete profiling result for a batch size/concurrency configuration."""

    batch_size: int
    concurrency_limit: int
    num_requests: int
    total_tokens: int
    duration_seconds: float
    tokens_per_second: float
    avg_gpu_load: float
    peak_gpu_load: float
    avg_temperature: float
    peak_temperature: float
    thermal_throttled: bool
    peak_memory_used: float  # MB
    cache_hit_rate: float


class GPUMonitor:
    """Monitor AMD Radeon GPU metrics during execution.

    Reads from /sys/kernel/debug/dri/0/ sysfs interface.
    Falls back to environment inspection if debugfs unavailable.
    """

    DEBUGFS_BASE = Path("/sys/kernel/debug/dri/0")

    def __init__(self) -> None:
        """Initialize GPU monitor."""
        self._snapshots: list[GPUMetrics] = []
        self._start_time: float | None = None
        self._is_measuring = False

    def start_measurement(self) -> None:
        """Begin collecting GPU metrics."""
        self._snapshots = []
        self._start_time = time.time()
        self._is_measuring = True
        logger.debug("GPU monitoring started")

    def stop_measurement(self) -> None:
        """Stop collecting GPU metrics."""
        self._is_measuring = False
        logger.debug(f"GPU monitoring stopped ({len(self._snapshots)} snapshots)")

    def collect_snapshot(self) -> GPUMetrics | None:
        """Collect single GPU metrics snapshot.

        Returns:
            GPUMetrics if successful, None if unavailable
        """
        if not self._is_measuring:
            return None

        try:
            metrics = self._read_gpu_metrics()
            if metrics:
                self._snapshots.append(metrics)
                return metrics
        except Exception as e:
            logger.debug(f"Failed to collect GPU snapshot: {e}")

        return None

    def _read_gpu_metrics(self) -> GPUMetrics | None:
        """Read GPU metrics from debugfs or sysfs."""
        timestamp = time.time()

        # Try debugfs first
        if self.DEBUGFS_BASE.exists():
            return self._read_from_debugfs(timestamp)

        # Fallback to rocm-smi or environment inspection
        return self._read_from_rocm_smi(timestamp)

    def _read_from_debugfs(self, timestamp: float) -> GPUMetrics | None:
        """Read metrics from /sys/kernel/debug/dri/0/ interface."""
        try:
            # Read GPU load (amdgpu_pm_info)
            pm_info_path = self.DEBUGFS_BASE / "amdgpu_pm_info"
            if not pm_info_path.exists():
                return None

            with open(pm_info_path) as f:
                pm_info = f.read()

            # Parse GPU load, temperatures, memory usage
            gpu_load = self._parse_gpu_load(pm_info)
            temperature = self._parse_temperature(pm_info)
            sclk, mclk = self._parse_clocks(pm_info)
            gpu_mem, gtt_mem = self._parse_memory(pm_info)
            throttle_status = self._parse_throttle_status(pm_info)

            return GPUMetrics(
                timestamp=timestamp,
                gpu_load=gpu_load,
                gpu_mem_used=gpu_mem,
                gtt_mem_used=gtt_mem,
                sclk=sclk,
                mclk=mclk,
                temperature=temperature,
                throttle_status=throttle_status,
            )
        except Exception as e:
            logger.debug(f"Failed to read from debugfs: {e}")
            return None

    def _read_from_rocm_smi(self, timestamp: float) -> GPUMetrics | None:
        """Fallback: read from rocm-smi if available."""
        try:
            import shutil

            rocm_smi = shutil.which("rocm-smi") or "/opt/rocm/bin/rocm-smi"
            result = subprocess.run(  # noqa: S603 - static probe with constant args
                [rocm_smi, "--json"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode != 0:
                return None

            # Parse JSON output (simplified)
            import json

            data = json.loads(result.stdout)
            if not data:
                return None

            gpu_data = data[0]  # First GPU
            gpu_load = float(gpu_data.get("gpu_load", 0).rstrip("%")) or 0
            temperature = float(gpu_data.get("temperature", "0 c").split()[0]) or 0
            gpu_mem = float(gpu_data.get("mem_used", "0").rstrip(" MB")) or 0
            sclk = float(gpu_data.get("sclk", "0").rstrip(" Mhz")) or 0
            mclk = float(gpu_data.get("mclk", "0").rstrip(" Mhz")) or 0

            throttle_status = "thermal" if temperature > 80 else "none"

            return GPUMetrics(
                timestamp=timestamp,
                gpu_load=gpu_load,
                gpu_mem_used=gpu_mem,
                gtt_mem_used=0,  # Not available from rocm-smi
                sclk=sclk,
                mclk=mclk,
                temperature=temperature,
                throttle_status=throttle_status,
            )
        except Exception as e:
            logger.debug(f"rocm-smi fallback failed: {e}")
            return None

    @staticmethod
    def _parse_gpu_load(pm_info: str) -> float:
        """Extract GPU load percentage from pm_info."""
        # Pattern: "GPU Load: 45%"
        match = re.search(r"GPU Load:\s*(\d+)%", pm_info)
        return float(match.group(1)) if match else 0.0

    @staticmethod
    def _parse_temperature(pm_info: str) -> float:
        """Extract GPU temperature from pm_info."""
        # Pattern: "Temperature: 52 C"
        match = re.search(r"Temperature:\s*(\d+)\s*[C°]", pm_info)
        return float(match.group(1)) if match else 0.0

    @staticmethod
    def _parse_clocks(pm_info: str) -> tuple[float, float]:
        """Extract GPU and memory clock frequencies from pm_info."""
        sclk = 0.0
        mclk = 0.0

        # Pattern: "SCLK: 400 Mhz"
        sclk_match = re.search(r"SCLK:\s*(\d+)\s*Mhz", pm_info)
        if sclk_match:
            sclk = float(sclk_match.group(1))

        # Pattern: "MCLK: 667 Mhz"
        mclk_match = re.search(r"MCLK:\s*(\d+)\s*Mhz", pm_info)
        if mclk_match:
            mclk = float(mclk_match.group(1))

        return sclk, mclk

    @staticmethod
    def _parse_memory(pm_info: str) -> tuple[float, float]:
        """Extract GPU VRAM and GTT memory usage from pm_info."""
        gpu_mem = 0.0
        gtt_mem = 0.0

        # Pattern: "VRAM: 256 MB"
        vram_match = re.search(r"VRAM:\s*(\d+)\s*MB", pm_info)
        if vram_match:
            gpu_mem = float(vram_match.group(1))

        # Pattern: "GTT: 1024 MB"
        gtt_match = re.search(r"GTT:\s*(\d+)\s*MB", pm_info)
        if gtt_match:
            gtt_mem = float(gtt_match.group(1))

        return gpu_mem, gtt_mem

    @staticmethod
    def _parse_throttle_status(pm_info: str) -> str:
        """Determine throttle status from pm_info."""
        if "Thermal throttle" in pm_info:
            return "thermal"
        if "Power throttle" in pm_info:
            return "power"
        return "none"

    def get_statistics(self) -> dict[str, Any]:
        """Compute statistics from collected snapshots.

        Returns:
            Dict with averages, peaks, and trends
        """
        if not self._snapshots:
            return {
                "avg_gpu_load": 0.0,
                "peak_gpu_load": 0.0,
                "avg_temperature": 0.0,
                "peak_temperature": 0.0,
                "thermal_throttled": False,
                "duration_seconds": 0.0,
            }

        gpu_loads = [s.gpu_load for s in self._snapshots]
        temperatures = [s.temperature for s in self._snapshots]
        throttle_statuses = [s.throttle_status for s in self._snapshots]

        duration = time.time() - (self._start_time or 0)

        return {
            "avg_gpu_load": statistics.mean(gpu_loads) if gpu_loads else 0.0,
            "peak_gpu_load": max(gpu_loads) if gpu_loads else 0.0,
            "avg_temperature": statistics.mean(temperatures) if temperatures else 0.0,
            "peak_temperature": max(temperatures) if temperatures else 0.0,
            "thermal_throttled": any(s == "thermal" for s in throttle_statuses),
            "duration_seconds": duration,
            "num_snapshots": len(self._snapshots),
        }


__all__ = [
    "GPUMetrics",
    "GPUMonitor",
    "ThermalProfilingResult",
]
