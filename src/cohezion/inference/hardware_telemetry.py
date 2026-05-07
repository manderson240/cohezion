"""
Hardware Telemetry - Local Silicon Utilization Tracking

Tracks actual hardware utilization for AMD Ryzen AI MAX+ 395 (Strix Halo):
- GPU (Radeon 8060S) via Vulkan/rocm-smi
- NPU (XDNA2) via FLM/firmware
- CPU (Zen 5) utilization
- Memory (128GB UMA) usage
- Thermals and throttling

Integrates with AutoHarness for hardware-aware optimization.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ComputeBackend(Enum):
    """Available compute backends."""

    VULKAN_GPU = "vulkan_gpu"
    ROCM_GPU = "rocm_gpu"  # Currently broken on gfx1151
    XDNA2_NPU = "xdna2_npu"
    ZEN5_CPU = "zen5_cpu"


@dataclass
class HardwareSnapshot:
    """Single hardware snapshot."""

    timestamp: float
    backend: ComputeBackend

    # Core metrics
    utilization_pct: float = 0.0
    memory_used_mb: int = 0
    memory_total_mb: int = 0
    temperature_c: float = 0.0

    # Performance
    compute_units_active: int = 0
    clock_mhz: float = 0.0

    # Status
    throttling: bool = False
    power_watts: float = 0.0


@dataclass
class UtilizationProfile:
    """Aggregated utilization profile."""

    backend: ComputeBackend
    duration_sec: float = 0.0

    # Averages
    avg_utilization: float = 0.0
    avg_memory_used_mb: float = 0.0
    avg_temperature: float = 0.0

    # Peaks
    peak_utilization: float = 0.0
    peak_memory_mb: int = 0
    peak_temperature: float = 0.0

    # Efficiency
    tokens_per_watt: float = 0.0
    tokens_per_cu: float = 0.0

    # Throttling
    throttled_time_sec: float = 0.0

    snapshots: list[HardwareSnapshot] = field(default_factory=list)


class HardwareTelemetry:
    """
    Hardware telemetry collector for AMD Strix Halo.

    Tracks actual silicon utilization to ensure we're maximizing
    local hardware, not just getting lucky with benchmarks.
    """

    def __init__(self, backend: ComputeBackend):
        self.backend = backend
        self.snapshots: list[HardwareSnapshot] = []
        self.start_time: float | None = None

        # Detection
        self._detect_tools()

    def _detect_tools(self):
        """Detect available monitoring tools."""
        self.has_rocm_smi = self._check_command("rocm-smi")
        self.has_amdgpu_pro = self._check_command("amdgpu-pro-px")
        self.has_flm = self._check_tool("/usr/bin/flm")
        self.has_perf = self._check_command("perf")

    def _check_command(self, cmd: str) -> bool:
        """Check if command exists."""
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _check_tool(self, path: str) -> bool:
        """Check if tool exists at path."""
        return Path(path).exists()

    def start(self):
        """Start telemetry collection."""
        self.start_time = time.monotonic()

    def snapshot(self) -> HardwareSnapshot:
        """Take a hardware snapshot."""
        snapshot = HardwareSnapshot(
            timestamp=time.monotonic(),
            backend=self.backend,
        )

        # Collect based on backend
        if self.backend == ComputeBackend.VULKAN_GPU:
            self._collect_vulkan_gpu(snapshot)
        elif self.backend == ComputeBackend.ROCM_GPU and self.has_rocm_smi:
            self._collect_rocm_gpu(snapshot)
        elif self.backend == ComputeBackend.XDNA2_NPU and self.has_flm:
            self._collect_xdna2_npu(snapshot)
        elif self.backend == ComputeBackend.ZEN5_CPU:
            self._collect_zen5_cpu(snapshot)

        self.snapshots.append(snapshot)
        return snapshot

    def _collect_vulkan_gpu(self, snapshot: HardwareSnapshot):
        """Collect Vulkan GPU metrics."""
        # Try amdgpu-pro first, then fallback to sysfs

        # Temperature from hwmon
        try:
            temp_files = list(Path("/sys/class/hwmon").glob("*/temp1_input"))
            if temp_files:
                temp_raw = temp_files[0].read_text().strip()
                snapshot.temperature_c = int(temp_raw) / 1000
        except Exception:
            pass

        # Memory from /proc/meminfo (UMA shared memory)
        try:
            meminfo = Path("/proc/meminfo").read_text()
            mem_total = re.search(r"MemTotal:\s+(\d+)", meminfo)
            mem_avail = re.search(r"MemAvailable:\s+(\d+)", meminfo)
            if mem_total and mem_avail:
                total_kb = int(mem_total.group(1))
                avail_kb = int(mem_avail.group(1))
                snapshot.memory_total_mb = total_kb // 1024
                snapshot.memory_used_mb = (total_kb - avail_kb) // 1024
        except Exception:
            pass

        # Attempt to get GPU utilization via process monitoring
        # This is imperfect for Vulkan - we estimate
        snapshot.utilization_pct = self._estimate_vulkan_utilization()

    def _estimate_vulkan_utilization(self) -> float:
        """
        Estimate GPU utilization for Vulkan.

        Since Vulkan doesn't expose utilization directly like ROCm,
        we estimate from process CPU time and memory patterns.
        """
        try:
            # Check if llama-server process exists and its state
            result = subprocess.run(["pgrep", "-f", "llama-server"], capture_output=True, text=True)

            if result.returncode == 0:
                # Process running - estimate based on load
                # This is a heuristic
                pid = result.stdout.strip().split("\n")[0]

                # Get CPU time
                stat = Path(f"/proc/{pid}/stat").read_text()
                utime = int(stat.split()[13])
                stime = int(stat.split()[14])

                # Very rough: if process is active, GPU is likely busy
                total_time = utime + stime
                return min(95.0, max(10.0, total_time / 1000))

        except Exception:
            pass

        return 0.0  # Unknown

    def _collect_rocm_gpu(self, snapshot: HardwareSnapshot):
        """Collect ROCm GPU metrics (if available)."""
        if not self.has_rocm_smi:
            return

        try:
            result = subprocess.run(
                ["rocm-smi", "--showtemp", "--showmeminfo", "vram", "--json"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data:
                    gpu_data = next(iter(data.values()))
                    snapshot.temperature_c = float(gpu_data.get("Temperature", {}).get("Sensor", 0))
                    vram_used = gpu_data.get("VRAM", {}).get("Used", "0 MB")
                    vram_total = gpu_data.get("VRAM", {}).get("Total", "0 MB")

                    snapshot.memory_used_mb = self._parse_memory(vram_used)
                    snapshot.memory_total_mb = self._parse_memory(vram_total)

                    # Utilization
                    util = gpu_data.get("GPU use (%)", "0%")
                    snapshot.utilization_pct = float(util.strip("%"))

        except Exception:
            snapshot.throttling = True  # Mark as failed

    def _collect_xdna2_npu(self, snapshot: HardwareSnapshot):
        """Collect XDNA2 NPU metrics."""
        if not self.has_flm:
            return

        # FLM doesn't expose detailed telemetry yet
        # We check if NPU is active via process
        try:
            result = subprocess.run(["pgrep", "-f", "flm"], capture_output=True)
            if result.returncode == 0:
                snapshot.utilization_pct = 100.0  # Active
        except Exception:
            pass

    def _collect_zen5_cpu(self, snapshot: HardwareSnapshot):
        """Collect Zen 5 CPU metrics."""
        # Load average
        try:
            loadavg = Path("/proc/loadavg").read_text()
            one_min_load = float(loadavg.split()[0])
            # Rough estimate: load / n_cpus * 100
            snapshot.utilization_pct = min(100.0, one_min_load * 100 / 16)
        except Exception:
            pass

        # Memory
        self._collect_vulkan_gpu(snapshot)  # Shared UMA

    def _parse_memory(self, mem_str: str) -> int:
        """Parse memory string to MB."""
        match = re.match(r"([\d.]+)\s*(\w+)", mem_str)
        if match:
            val = float(match.group(1))
            unit = match.group(2).lower()
            if "gb" in unit:
                return int(val * 1024)
            elif "mb" in unit:
                return int(val)
        return 0

    def finish(self) -> UtilizationProfile:
        """Finish collection and generate profile."""
        if not self.start_time:
            return UtilizationProfile(backend=self.backend)

        duration = time.monotonic() - self.start_time

        if not self.snapshots:
            return UtilizationProfile(backend=self.backend, duration_sec=duration)

        # Calculate stats
        utils = [s.utilization_pct for s in self.snapshots if s.utilization_pct > 0]
        mems = [s.memory_used_mb for s in self.snapshots]
        temps = [s.temperature_c for s in self.snapshots if s.temperature_c > 0]

        throttled = sum(1 for s in self.snapshots if s.throttling)

        return UtilizationProfile(
            backend=self.backend,
            duration_sec=duration,
            avg_utilization=sum(utils) / len(utils) if utils else 0,
            avg_memory_used_mb=sum(mems) / len(mems) if mems else 0,
            avg_temperature=sum(temps) / len(temps) if temps else 0,
            peak_utilization=max(utils) if utils else 0,
            peak_memory_mb=max(mems) if mems else 0,
            peak_temperature=max(temps) if temps else 0,
            throttled_time_sec=throttled * 5,  # Assuming 5s intervals
            snapshots=self.snapshots,
        )

    def get_current_status(self) -> dict:
        """Get current hardware status for display."""
        if not self.snapshots:
            return {"status": "No data"}

        latest = self.snapshots[-1]

        return {
            "backend": self.backend.value,
            "temperature_c": latest.temperature_c,
            "utilization_pct": latest.utilization_pct,
            "memory_used_gb": latest.memory_used_mb / 1024,
            "throttling": latest.throttling,
            "health": self._assess_health(latest),
        }

    def _assess_health(self, snapshot: HardwareSnapshot) -> str:
        """Assess hardware health."""
        if snapshot.temperature_c > 85:
            return "CRITICAL - Throttling likely"
        elif snapshot.temperature_c > 75:
            return "WARNING - Hot"
        elif snapshot.utilization_pct < 50 and len(self.snapshots) > 10:
            return "WARNING - Underutilized"
        elif snapshot.utilization_pct > 90:
            return "GOOD - Well utilized"
        return "OK"


class MultiBackendTelemetry:
    """
    Telemetry collector for all available backends.

    Tracks how well we're utilizing all available silicon:
    - GPU (Vulkan): Primary
    - NPU (XDNA2): Secondary
    - CPU (Zen 5): Fallback
    """

    def __init__(self):
        self.telemetries: dict[ComputeBackend, HardwareTelemetry] = {}
        self.profiles: dict[ComputeBackend, UtilizationProfile] = {}

    def add_backend(self, backend: ComputeBackend):
        """Add a backend to monitor."""
        self.telemetries[backend] = HardwareTelemetry(backend)

    def start_all(self):
        """Start all telemetry."""
        for tel in self.telemetries.values():
            tel.start()

    def snapshot_all(self) -> dict[ComputeBackend, HardwareSnapshot]:
        """Snapshot all backends."""
        results = {}
        for backend, tel in self.telemetries.items():
            results[backend] = tel.snapshot()
        return results

    def finish_all(self) -> dict[ComputeBackend, UtilizationProfile]:
        """Finish all telemetry and get profiles."""
        for backend, tel in self.telemetries.items():
            self.profiles[backend] = tel.finish()
        return self.profiles

    def report(self) -> str:
        """Generate multi-backend utilization report."""
        lines = [
            "=" * 70,
            "HARDWARE TELEMETRY REPORT",
            "AMD Ryzen AI MAX+ 395 (Strix Halo)",
            "=" * 70,
            "",
        ]

        for backend, profile in self.profiles.items():
            lines.append(f"{backend.value.upper()}:")
            lines.append(f"  Duration: {profile.duration_sec:.1f}s")
            lines.append(
                f"  Utilization: {profile.avg_utilization:.1f}% (peak: {profile.peak_utilization:.1f}%)"
            )
            lines.append(
                f"  Memory: {profile.avg_memory_used_mb / 1024:.1f}GB (peak: {profile.peak_memory_mb / 1024:.1f}GB)"
            )
            lines.append(
                f"  Temperature: {profile.avg_temperature:.1f}°C (peak: {profile.peak_temperature:.1f}°C)"
            )

            if profile.throttled_time_sec > 0:
                lines.append(f"  ⚠️ Throttled: {profile.throttled_time_sec:.1f}s")

            lines.append("")

        # Overall assessment
        lines.append("--- OVERALL ASSESSMENT ---")

        total_util = sum(p.avg_utilization for p in self.profiles.values())
        avg_util = total_util / len(self.profiles) if self.profiles else 0

        lines.append(f"Average silicon utilization: {avg_util:.1f}%")

        if avg_util < 50:
            lines.append("❌ UNDERUTILIZED - We're not maximizing hardware")
        elif avg_util > 85:
            lines.append("⚠️ SATURATED - May be thermal/power limiting")
        else:
            lines.append("✅ GOOD - Well-balanced utilization")

        lines.append("=" * 70)

        return "\n".join(lines)


# Integration with autoharness
class HardwareAwareAutoharness:
    """
    Hardware-aware autoharness that optimizes for actual silicon utilization.
    """

    def __init__(self, model_id: str):
        self.model_id = model_id
        self.telemetry = MultiBackendTelemetry()

        # Add primary backend
        self.telemetry.add_backend(ComputeBackend.VULKAN_GPU)

    def run_hardware_aware_experiment(self, config: dict, runner: Callable) -> dict:
        """
        Run experiment with full hardware telemetry.

        Returns result enriched with actual hardware utilization data.
        """
        # Start telemetry
        self.telemetry.start_all()

        # Run experiment
        result = runner(config)

        # Get profiles
        profiles = self.telemetry.finish_all()

        # Enrich result
        result["hardware"] = {
            "profiles": {
                k.value: {
                    "avg_utilization": p.avg_utilization,
                    "peak_utilization": p.peak_utilization,
                    "avg_temp_c": p.avg_temperature,
                    "peak_temp_c": p.peak_temperature,
                    "throttled_time_sec": p.throttled_time_sec,
                }
                for k, p in profiles.items()
            },
            "telemetry_report": self.telemetry.report(),
        }

        # Calculate hardware efficiency
        gpu_profile = profiles.get(ComputeBackend.VULKAN_GPU)
        if gpu_profile and result.get("tokens_per_sec", 0) > 0:
            # Tokens per watt estimate (rough)
            result["hardware"]["tokens_per_watt"] = (
                result["tokens_per_sec"] / 65  # Assuming 65W TDP
            )

            # Utilization efficiency
            result["hardware"]["utilization_efficiency"] = gpu_profile.avg_utilization / 100.0

        return result


def create_hardware_telemetry(backend: ComputeBackend) -> HardwareTelemetry:
    """Factory for hardware telemetry."""
    return HardwareTelemetry(backend)


if __name__ == "__main__":
    # Demo
    print("Hardware Telemetry Demo")
    print("=" * 50)

    # Start telemetry
    tel = HardwareTelemetry(ComputeBackend.VULKAN_GPU)
    tel.start()

    # Collect for 3 seconds
    for i in range(3):
        time.sleep(1)
        snap = tel.snapshot()
        print(f"Snapshot {i + 1}: {snap.utilization_pct:.1f}% util, {snap.temperature_c:.1f}°C")

    # Finish
    profile = tel.finish()
    print(f"\nProfile: {profile.avg_utilization:.1f}% avg util")
    print(f"         {profile.peak_temperature:.1f}°C peak temp")
