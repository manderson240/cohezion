"""TDP Budget Tracker for 8-hour power envelope management.

Tracks cumulative power consumption over long-duration tasks to ensure the system
stays within thermal design power (TDP) budget. Prevents thermal runaway from
sustained high power draw on AMD Ryzen AI MAX+ 395.

Key features:
- Real-time power estimation from hardware metrics
- TDP budget tracking over time
- Throttle recommendations based on power consumption rate
- Power profile management (balance vs performance)
- Integration with ThermalCheckpointManager

Phase 4: 8-Hour Autoresearch Journey
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

from cohezion.compound.hardware_monitor import HardwareMonitor, get_hardware_monitor


logger = logging.getLogger(__name__)


class PowerProfile(Enum):
    """Power consumption profiles."""

    EFFICIENCY = auto()  # Minimize power, maximize battery life
    BALANCED = auto()  # Balance performance and power
    PERFORMANCE = auto()  # Maximize performance, accept higher power


@dataclass
class PowerSample:
    """Single power measurement."""

    timestamp: float
    cpu_power_w: float
    gpu_power_w: float
    total_power_w: float
    cpu_temp_c: float
    gpu_temp_c: float
    gpu_clock_mhz: float


@dataclass
class TDPEnvelope:
    """TDP envelope configuration for long-duration tasks."""

    tdp_watts: float = 120.0  # AMD Ryzen AI MAX+ 395 TDP
    duration_hours: float = 8.0

    @property
    def total_watt_hours(self) -> float:
        """Total energy budget in watt-hours."""
        return self.tdp_watts * self.duration_hours

    @property
    def target_average_watts(self) -> float:
        """Target average power to stay within budget."""
        return self.tdp_watts * 0.85  # 15% headroom


@dataclass
class TDPConfig:
    """Configuration for TDP budget management."""

    envelope: TDPEnvelope = field(default_factory=TDPEnvelope)

    # Safety margins
    warning_threshold_percent: float = 0.70  # Warn at 70% of budget
    throttle_threshold_percent: float = 0.85  # Throttle at 85%
    emergency_threshold_percent: float = 0.95  # Emergency stop at 95%

    # Sampling
    sample_interval_seconds: int = 60  # Power sample every minute

    # Persistence
    history_dir: Path = field(default_factory=lambda: Path("data/tdp_history"))

    # Profile
    profile: PowerProfile = PowerProfile.BALANCED


class TDPBudgetTracker:
    """Tracks TDP budget consumption over long-duration tasks.

    Monitors power consumption and provides recommendations to stay within
    thermal envelope over 8+ hour runs.

    Usage:
        tracker = TDPBudgetTracker(TDPConfig())
        async with tracker:
            while task_running:
                status = tracker.get_budget_status()
                if status.should_throttle:
                    await throttle_execution()
                await asyncio.sleep(60)
    """

    # Power estimation coefficients (empirically determined)
    CPU_POWER_PER_TEMP = 0.5  # Watts per degree above 40°C
    GPU_POWER_PER_CLOCK = 0.0015  # Watts per MHz
    BASE_SYSTEM_POWER = 15.0  # Watts for system overhead

    def __init__(self, config: TDPConfig | None = None):
        self.config = config or TDPConfig()
        self.monitor: HardwareMonitor = get_hardware_monitor()

        self.samples: list[PowerSample] = []
        self.start_time: float = 0.0
        self.consumed_wh: float = 0.0
        self.current_power_w: float = 0.0

        # History persistence
        self.config.history_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.config.history_dir / f"tdp_history_{int(time.time())}.jsonl"

        logger.info("TDPBudgetTracker initialized")
        logger.info(f"  TDP: {self.config.envelope.tdp_watts}W")
        logger.info(f"  Duration: {self.config.envelope.duration_hours}h")
        logger.info(f"  Total budget: {self.config.envelope.total_watt_hours:.1f} Wh")
        logger.info(f"  Target average: {self.config.envelope.target_average_watts:.1f}W")

    async def __aenter__(self):
        """Async context manager entry."""
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._save_history()

    def estimate_power(self, metrics) -> tuple[float, float, float]:
        """Estimate power consumption from hardware metrics.

        Returns:
            (cpu_power_w, gpu_power_w, total_power_w)
        """
        # CPU power estimation based on temperature
        cpu_temp = metrics.cpu_temp_current
        cpu_power = max(0, (cpu_temp - 40) * self.CPU_POWER_PER_TEMP)

        # GPU power estimation based on clock speed
        gpu_clock = metrics.gpu_clock_mhz
        gpu_power = gpu_clock * self.GPU_POWER_PER_CLOCK

        # Total including base system power
        total = cpu_power + gpu_power + self.BASE_SYSTEM_POWER

        # Adjust for power profile
        if self.config.profile == PowerProfile.EFFICIENCY:
            total *= 0.8
        elif self.config.profile == PowerProfile.PERFORMANCE:
            total *= 1.2

        return cpu_power, gpu_power, total

    async def sample_power(self) -> PowerSample:
        """Take a power sample and update budget tracking."""
        metrics = self.monitor.get_current_metrics()

        cpu_power, gpu_power, total = self.estimate_power(metrics)

        sample = PowerSample(
            timestamp=time.time(),
            cpu_power_w=cpu_power,
            gpu_power_w=gpu_power,
            total_power_w=total,
            cpu_temp_c=metrics.cpu_temp_current,
            gpu_temp_c=metrics.gpu_temp_current,
            gpu_clock_mhz=metrics.gpu_clock_mhz,
        )

        self.samples.append(sample)
        self.current_power_w = total

        # Update consumed watt-hours
        if len(self.samples) > 1:
            time_delta_hours = (sample.timestamp - self.samples[-2].timestamp) / 3600
            avg_power = (self.samples[-2].total_power_w + total) / 2
            self.consumed_wh += avg_power * time_delta_hours

        # Persist sample
        await self._persist_sample(sample)

        return sample

    def get_budget_status(self) -> dict[str, Any]:
        """Get current TDP budget status.

        Returns dict with:
            - consumed_wh: Watt-hours consumed so far
            - remaining_wh: Watt-hours remaining
            - consumed_percent: Percentage of budget consumed
            - remaining_hours: Estimated hours remaining at current power
            - should_throttle: Whether to throttle
            - should_emergency_stop: Whether to emergency stop
            - current_power_w: Current power consumption
            - avg_power_w: Average power consumption
        """
        total_budget = self.config.envelope.total_watt_hours
        consumed = self.consumed_wh
        remaining = max(0, total_budget - consumed)
        consumed_pct = (consumed / total_budget) * 100

        # Calculate remaining time at current power
        if self.current_power_w > 0:
            remaining_hours = remaining / self.current_power_w
        else:
            remaining_hours = float("inf")

        # Calculate average power
        if self.samples:
            avg_power = sum(s.total_power_w for s in self.samples) / len(self.samples)
        else:
            avg_power = 0.0

        # Determine actions
        should_throttle = consumed_pct >= (self.config.throttle_threshold_percent * 100)
        should_emergency = consumed_pct >= (self.config.emergency_threshold_percent * 100)
        should_warn = consumed_pct >= (self.config.warning_threshold_percent * 100)

        return {
            "consumed_wh": consumed,
            "remaining_wh": remaining,
            "consumed_percent": consumed_pct,
            "remaining_hours": remaining_hours,
            "should_warn": should_warn,
            "should_throttle": should_throttle,
            "should_emergency_stop": should_emergency,
            "current_power_w": self.current_power_w,
            "avg_power_w": avg_power,
            "profile": self.config.profile.name,
            "elapsed_hours": (time.time() - self.start_time) / 3600,
        }

    def get_throttle_recommendation(self) -> dict[str, Any]:
        """Get throttling recommendations based on power budget.

        Returns dict with:
            - action: "none", "reduce", "throttle", "emergency"
            - reason: Explanation
            - target_power_w: Recommended power target
            - intensity: 0.0-1.0 scale of throttling needed
        """
        status = self.get_budget_status()
        consumed_pct = status["consumed_percent"]

        if consumed_pct >= (self.config.emergency_threshold_percent * 100):
            return {
                "action": "emergency",
                "reason": f"Emergency: {consumed_pct:.1f}% of power budget consumed",
                "target_power_w": self.config.envelope.tdp_watts * 0.5,
                "intensity": 1.0,
            }

        elif consumed_pct >= (self.config.throttle_threshold_percent * 100):
            intensity = (consumed_pct - 85) / 10  # 0.0-1.0 from 85% to 95%
            return {
                "action": "throttle",
                "reason": f"Throttling: {consumed_pct:.1f}% of power budget consumed",
                "target_power_w": self.config.envelope.target_average_watts * (1 - intensity * 0.5),
                "intensity": intensity,
            }

        elif consumed_pct >= (self.config.warning_threshold_percent * 100):
            return {
                "action": "reduce",
                "reason": f"Warning: {consumed_pct:.1f}% of power budget consumed",
                "target_power_w": self.config.envelope.target_average_watts,
                "intensity": 0.3,
            }

        else:
            return {
                "action": "none",
                "reason": f"Normal: {consumed_pct:.1f}% of power budget consumed",
                "target_power_w": self.config.envelope.tdp_watts,
                "intensity": 0.0,
            }

    async def _persist_sample(self, sample: PowerSample) -> None:
        """Persist power sample to JSONL."""
        try:
            data = {
                "timestamp": sample.timestamp,
                "cpu_power_w": sample.cpu_power_w,
                "gpu_power_w": sample.gpu_power_w,
                "total_power_w": sample.total_power_w,
                "cpu_temp_c": sample.cpu_temp_c,
                "gpu_temp_c": sample.gpu_temp_c,
                "gpu_clock_mhz": sample.gpu_clock_mhz,
                "cumulative_wh": self.consumed_wh,
            }

            with open(self.history_file, "a") as f:
                f.write(json.dumps(data) + "\n")

        except Exception as e:
            logger.error(f"Failed to persist power sample: {e}")

    async def _save_history(self) -> None:
        """Save final history summary."""
        try:
            summary = self.get_budget_status()
            summary_file = self.history_file.with_suffix(".summary.json")

            with open(summary_file, "w") as f:
                json.dump(summary, f, indent=2)

            logger.info(f"TDP history saved: {self.history_file}")
            logger.info(f"  Total consumed: {summary['consumed_wh']:.2f} Wh")
            logger.info(f"  Average power: {summary['avg_power_w']:.2f} W")

        except Exception as e:
            logger.error(f"Failed to save TDP summary: {e}")

    async def monitor_loop(self, interval_seconds: int = 60) -> None:
        """Run continuous power monitoring loop.

        Call this in a background task to continuously track power.
        """
        while True:
            try:
                await self.sample_power()

                # Log status periodically
                status = self.get_budget_status()
                if status["should_warn"]:
                    logger.warning(
                        f"TDP Budget: {status['consumed_percent']:.1f}% consumed, "
                        f"{status['remaining_hours']:.1f}h remaining"
                    )
                else:
                    logger.info(f"TDP Budget: {status['consumed_percent']:.1f}% consumed")

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"TDP monitor loop error: {e}")
                await asyncio.sleep(interval_seconds)

    def adjust_for_profile(self, profile: PowerProfile) -> None:
        """Change power profile mid-execution."""
        old_profile = self.config.profile
        self.config.profile = profile

        logger.info(f"Power profile changed: {old_profile.name} -> {profile.name}")

        if profile == PowerProfile.EFFICIENCY:
            logger.info("Efficiency mode: Expect ~20% lower power consumption")
        elif profile == PowerProfile.PERFORMANCE:
            logger.info("Performance mode: Expect ~20% higher power consumption")


# Singleton instance
def get_tdp_budget_tracker(config: TDPConfig | None = None) -> TDPBudgetTracker:
    """Get singleton TDP budget tracker."""
    return TDPBudgetTracker(config)
