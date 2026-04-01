"""System hardware metrics collection for thermal-aware execution.

Collects CPU/GPU temperature, power draw, and thermal throttling information
from system interfaces. Enables thermal-aware batch sizing by predicting
temperature impact of workloads.

Key interfaces:
- /sys/class/thermal/ (CPU temps)
- amdgpu sysfs (GPU temps, clock speeds)
- /sys/class/powercap/ (power draw)

Fallback: Reasonable defaults for testing (no real hardware required).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class HardwareMetrics:
    """Current hardware state snapshot."""

    cpu_temp_current: float  # °C, from /sys/class/thermal/
    gpu_temp_current: float  # °C, from amdgpu driver
    cpu_power: float  # watts
    gpu_power: float  # watts
    memory_used: float  # GB
    timestamp: float  # seconds since epoch
    gpu_clock_mhz: float = 2800.0  # Current GPU clock (MHz)
    gpu_max_clock_mhz: float = 2800.0  # Max GPU clock (MHz)


class HardwareMonitor:
    """Collects thermal and power metrics from system interfaces.

    Linux-only implementation:
    - CPU temps: /sys/class/thermal/thermal_zone*/temp
    - GPU temps: /sys/class/drm/card*/device/hwmon/*/temp*
    - GPU clocks: /sys/class/drm/card*/device/pp_sclk
    - Power: /sys/class/powercap/intel-rapl*/energy_uj

    Graceful fallback to defaults when hardware unavailable.
    """

    # Default safe temperature estimate
    DEFAULT_CPU_TEMP = 55.0  # °C
    DEFAULT_GPU_TEMP = 60.0  # °C
    DEFAULT_CPU_POWER = 25.0  # watts
    DEFAULT_GPU_POWER = 15.0  # watts
    DEFAULT_MEMORY_USED = 2.0  # GB

    # Thermal limits
    THERMAL_THROTTLE_START = 92.0  # °C
    THERMAL_CRITICAL = 95.0  # °C

    def __init__(self, enable_real_hardware: bool = True) -> None:
        """Initialize hardware monitor.

        Args:
            enable_real_hardware: If True, try to read real metrics
        """
        self.enable_real_hardware = enable_real_hardware
        self._hardware_available = False

        # Try to detect available hardware paths
        if enable_real_hardware:
            self._detect_hardware_paths()

    def _detect_hardware_paths(self) -> None:
        """Detect available hardware metric paths."""
        try:
            # Check for thermal zones
            thermal_path = Path("/sys/class/thermal")
            if thermal_path.exists():
                self._hardware_available = True
                logger.debug(f"Hardware metrics available: found thermal_path={thermal_path}")
            else:
                logger.debug("Hardware metrics unavailable: no /sys/class/thermal found")
        except Exception as e:
            logger.debug(f"Hardware detection error: {e}")
            self._hardware_available = False

    def get_current_metrics(self) -> HardwareMetrics:
        """Get current hardware state."""
        if not self.enable_real_hardware or not self._hardware_available:
            return HardwareMetrics(
                cpu_temp_current=self.DEFAULT_CPU_TEMP,
                gpu_temp_current=self.DEFAULT_GPU_TEMP,
                cpu_power=self.DEFAULT_CPU_POWER,
                gpu_power=self.DEFAULT_GPU_POWER,
                memory_used=self.DEFAULT_MEMORY_USED,
                timestamp=time.time(),
            )

        try:
            cpu_temp = self._read_cpu_temp()
            gpu_temp = self._read_gpu_temp()
            cpu_power = self._read_cpu_power()
            gpu_power = self._read_gpu_power()
            memory_used = self._read_memory_used()
            gpu_clock = self._read_gpu_clock()

            return HardwareMetrics(
                cpu_temp_current=cpu_temp,
                gpu_temp_current=gpu_temp,
                cpu_power=cpu_power,
                gpu_power=gpu_power,
                memory_used=memory_used,
                timestamp=time.time(),
                gpu_clock_mhz=gpu_clock,
                gpu_max_clock_mhz=2800.0,
            )
        except Exception as e:
            logger.debug(f"Error reading hardware metrics: {e}")
            return HardwareMetrics(
                cpu_temp_current=self.DEFAULT_CPU_TEMP,
                gpu_temp_current=self.DEFAULT_GPU_TEMP,
                cpu_power=self.DEFAULT_CPU_POWER,
                gpu_power=self.DEFAULT_GPU_POWER,
                memory_used=self.DEFAULT_MEMORY_USED,
                timestamp=time.time(),
            )

    def _read_cpu_temp(self) -> float:
        """Read CPU temperature from thermal zones."""
        try:
            thermal_path = Path("/sys/class/thermal")
            max_temp = self.DEFAULT_CPU_TEMP

            for zone in thermal_path.glob("thermal_zone*/temp"):
                try:
                    temp_millidegree = int(zone.read_text().strip())
                    temp_celsius = temp_millidegree / 1000.0
                    max_temp = max(max_temp, temp_celsius)
                except (ValueError, OSError):
                    continue

            return max_temp
        except Exception as e:
            logger.debug("CPU temp read failed, using default: %s", e)
            return self.DEFAULT_CPU_TEMP

    def _read_gpu_temp(self) -> float:
        """Read GPU temperature from amdgpu driver."""
        try:
            drm_path = Path("/sys/class/drm")
            max_temp = self.DEFAULT_GPU_TEMP

            for hwmon_dir in drm_path.glob("card*/device/hwmon/hwmon*"):
                for temp_file in hwmon_dir.glob("temp*_input"):
                    try:
                        temp_millidegree = int(temp_file.read_text().strip())
                        temp_celsius = temp_millidegree / 1000.0
                        max_temp = max(max_temp, temp_celsius)
                    except (ValueError, OSError):
                        continue

            return max_temp
        except Exception as e:
            logger.debug("GPU temp read failed, using default: %s", e)
            return self.DEFAULT_GPU_TEMP

    def _read_cpu_power(self) -> float:
        """Read CPU power draw from RAPL interface."""
        try:
            rapl_path = Path("/sys/class/powercap")
            total_power = self.DEFAULT_CPU_POWER

            for rapl_dir in rapl_path.glob("intel-rapl:*"):
                energy_file = rapl_dir / "energy_uj"
                if energy_file.exists():
                    try:
                        energy_uj = int(energy_file.read_text().strip())
                        total_power = max(
                            self.DEFAULT_CPU_POWER,
                            min(100.0, energy_uj / 1e6 / 60.0),
                        )
                    except (ValueError, OSError):
                        continue

            return total_power
        except Exception as e:
            logger.debug("CPU power read failed, using default: %s", e)
            return self.DEFAULT_CPU_POWER

    def _read_gpu_power(self) -> float:
        """Read GPU power draw estimate."""
        try:
            gpu_clock = self._read_gpu_clock()
            normalized_clock = gpu_clock / 2800.0
            power = 25.0 * (normalized_clock**2)
            return max(self.DEFAULT_GPU_POWER, min(50.0, power))
        except Exception as e:
            logger.debug("GPU power read failed, using default: %s", e)
            return self.DEFAULT_GPU_POWER

    def _read_gpu_clock(self) -> float:
        """Read current GPU clock speed."""
        try:
            for pp_sclk in Path("/sys/class/drm").glob("card*/device/pp_sclk"):
                try:
                    content = pp_sclk.read_text().strip()
                    for line in content.split("\n"):
                        if "*" in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                mhz_str = parts[1].replace("Mhz", "")
                                return float(mhz_str)
                except (ValueError, OSError):
                    continue

            return 2800.0
        except Exception as e:
            logger.debug("GPU clock read failed, using default: %s", e)
            return 2800.0

    def _read_memory_used(self) -> float:
        """Read memory usage."""
        try:
            with open("/proc/meminfo") as f:
                meminfo = {}
                for line in f:
                    key, value = line.split(":", 1)
                    meminfo[key.strip()] = int(value.split()[0])

            total = meminfo.get("MemTotal", 16384) / 1024.0 / 1024.0  # GB
            available = meminfo.get("MemAvailable", 8192) / 1024.0 / 1024.0
            used = total - available

            return max(self.DEFAULT_MEMORY_USED, min(total, used))
        except Exception:
            return self.DEFAULT_MEMORY_USED

    def get_stats(self) -> dict:
        """Get hardware monitor statistics."""
        metrics = self.get_current_metrics()

        return {
            "hardware_available": self._hardware_available,
            "current_cpu_temp_c": metrics.cpu_temp_current,
            "current_gpu_temp_c": metrics.gpu_temp_current,
            "current_cpu_power_w": metrics.cpu_power,
            "current_gpu_power_w": metrics.gpu_power,
            "current_memory_used_gb": metrics.memory_used,
            "gpu_clock_mhz": metrics.gpu_clock_mhz,
            "gpu_max_clock_mhz": metrics.gpu_max_clock_mhz,
        }


# Module-level singleton
_monitor_instance: HardwareMonitor | None = None


def get_hardware_monitor() -> HardwareMonitor:
    """Get or create singleton hardware monitor."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = HardwareMonitor()
    return _monitor_instance
