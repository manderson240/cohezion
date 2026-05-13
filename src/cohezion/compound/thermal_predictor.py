"""Predictive thermal management for preventing GPU throttling.

Learns thermal patterns from execution history and predicts temperature impact
of new workloads. Enables thermal-aware batch sizing by recommending batch
sizes that stay within safe operating limits.

Phase 3 Sprint 2: Predictive Thermal Throttling

Key features:
- In-memory history of thermal metrics per task type
- Linear regression model: batch_size → peak_temperature
- Throttle probability prediction via sigmoid function
- Binary search for maximum safe batch size
- Graceful fallback when history unavailable
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class ThermalMetrics:
    """Metrics from a batch execution for thermal learning."""

    batch_size: int
    task_count: int
    task_types: list[str]
    duration_seconds: float
    tokens_used: int
    peak_gpu_temp: float  # °C
    peak_cpu_temp: float  # °C
    throttle_detected: bool
    throttle_percentage: float  # 0-100
    execution_power_watts: float  # average power draw
    errors: int = 0
    timestamp: str = field(default_factory=lambda: "")

    @property
    def primary_task_type(self) -> str:
        """Most common task type in batch."""
        if not self.task_types:
            return "unknown"
        return max(set(self.task_types), key=self.task_types.count)

    @property
    def tokens_per_second(self) -> float:
        """Tokens per second throughput."""
        if self.duration_seconds <= 0:
            return 0.0
        return self.tokens_used / self.duration_seconds


class ThermalTrendAnalyzer:
    """Learns thermal patterns and predicts safe batch sizes.

    Maintains in-memory history of batch executions and predicts temperature
    impact based on:
    - Task type (generate, analyze, search, transform, persist)
    - Batch size (number of tasks)
    - Expected duration
    - Historical thermal trends

    Parameters
    ----------
    history_size : int
        Maximum number of execution records to keep in memory (default: 200)
    target_temp_celsius : float
        Target operating temperature (default: 85.0°C, safety margin below 92°C throttle point)
    vault_client : optional
        VaultClient for persistent learning (Phase 2)
    """

    # Thermal limits (AMD Ryzen AI MAX+ 395)
    THERMAL_THROTTLE_POINT = 92.0  # °C - throttling begins
    THERMAL_CRITICAL = 95.0  # °C - emergency fallback
    NORMAL_OPERATING_RANGE = 50.0  # °C - idle baseline

    # Heuristic base temperatures per task type (starting point for learning)
    BASE_TEMPS = {
        "generate": 72.0,  # Slow, compute-heavy
        "analyze": 68.0,  # Medium compute
        "search": 65.0,  # Fast, less compute
        "transform": 68.0,  # Medium
        "persist": 66.0,  # I/O mostly
        "unknown": 70.0,  # Default
    }

    # Temperature ramp rates (°C per second under load)
    RAMP_RATES = {
        "generate": 0.8,  # Fast heating
        "analyze": 0.5,
        "search": 0.3,
        "transform": 0.5,
        "persist": 0.2,
        "unknown": 0.5,
    }

    def __init__(
        self,
        history_size: int = 200,
        target_temp_celsius: float = 85.0,
        vault_client: Any | None = None,
    ) -> None:
        """Initialize thermal trend analyzer."""
        self.history_size = history_size
        self.target_temp_celsius = target_temp_celsius
        self.vault_client = vault_client

        # In-memory history: {task_type: [metrics]}
        self.history: dict[str, list[ThermalMetrics]] = {}
        self._last_prediction: tuple[float, float] | None = None  # (temp, confidence)

    def record_execution(self, metrics: ThermalMetrics) -> None:
        """Record a batch execution for thermal learning.

        Parameters
        ----------
        metrics : ThermalMetrics
            Metrics from batch execution including peak temperatures
        """
        task_type = metrics.primary_task_type

        if task_type not in self.history:
            self.history[task_type] = []

        self.history[task_type].append(metrics)

        # Limit history size (keep most recent)
        if len(self.history[task_type]) > self.history_size:
            self.history[task_type] = self.history[task_type][-self.history_size :]

        logger.debug(
            f"Recorded thermal execution: batch_size={metrics.batch_size} "
            f"peak_gpu_temp={metrics.peak_gpu_temp:.1f}°C "
            f"task_type={task_type} "
            f"throttle={'YES' if metrics.throttle_detected else 'NO'}"
        )

    def predict_thermal_safety(self, task_type: str, batch_size: int, duration_sec: float) -> float:
        """Predict peak GPU temperature for a workload.

        Uses linear regression model: temp = base + (batch_size * slope) + (duration * ramp)

        Parameters
        ----------
        task_type : str
            Type of task (generate, analyze, search, transform, persist)
        batch_size : int
            Number of tasks to batch
        duration_sec : float
            Expected execution time in seconds

        Returns
        -------
        float
            Predicted peak temperature (°C)
        """
        if not task_type or task_type not in self.BASE_TEMPS:
            task_type = "unknown"

        # Get history for this task type
        type_history = self.history.get(task_type, [])

        if not type_history:
            # No history: use heuristic model
            base_temp = self.BASE_TEMPS[task_type]
            ramp_rate = self.RAMP_RATES[task_type]
            # Simple linear: temp = base + (batch_size / 32) * 5 + duration * ramp
            predicted = base_temp + (batch_size / 32.0 * 5.0) + (duration_sec * ramp_rate)
            return predicted

        # Analyze historical thermal data by batch size
        predicted = self._predict_from_history(type_history, batch_size, duration_sec, task_type)
        return predicted

    def _predict_from_history(
        self,
        history: list[ThermalMetrics],
        batch_size: int,
        duration_sec: float,
        task_type: str,
    ) -> float:
        """Predict temperature from historical data using linear regression.

        Parameters
        ----------
        history : list[ThermalMetrics]
            Historical execution data
        batch_size : int
            Batch size to predict for
        duration_sec : float
            Expected duration
        task_type : str
            Task type for fallback

        Returns
        -------
        float
            Predicted temperature (°C)
        """
        if not history:
            return self.BASE_TEMPS.get(task_type, 70.0)

        # Extract features and targets
        batch_sizes = [m.batch_size for m in history]
        temps = [m.peak_gpu_temp for m in history]

        if len(batch_sizes) < 2:
            # Not enough data: return average + margin
            avg_temp = sum(temps) / len(temps) if temps else self.BASE_TEMPS[task_type]
            return avg_temp + 2.0  # Conservative margin

        # Simple linear regression: temp = a + b * batch_size
        n = len(batch_sizes)
        mean_batch = sum(batch_sizes) / n
        mean_temp = sum(temps) / n

        # Calculate slope
        numerator = sum((batch_sizes[i] - mean_batch) * (temps[i] - mean_temp) for i in range(n))
        denominator = sum((b - mean_batch) ** 2 for b in batch_sizes)

        if abs(denominator) < 0.01:
            # No correlation: return average
            return mean_temp + 2.0

        slope = numerator / denominator
        intercept = mean_temp - slope * mean_batch

        # Predict for new batch_size
        predicted = intercept + slope * batch_size

        # Add temperature ramp from duration
        ramp_rate = self.RAMP_RATES.get(task_type, 0.5)
        predicted += duration_sec * ramp_rate * 0.1  # Moderate impact

        return predicted

    def get_safe_batch_size(self, task_type: str, target_temp: float | None = None) -> int:
        """Find maximum safe batch size via binary search.

        Parameters
        ----------
        task_type : str
            Type of task
        target_temp : float, optional
            Target temperature (default: self.target_temp_celsius)

        Returns
        -------
        int
            Maximum recommended batch size
        """
        if target_temp is None:
            target_temp = self.target_temp_celsius

        # Binary search for maximum safe batch size
        # Assume 1 second duration for safety estimation
        min_batch = 1
        max_batch = 256  # Reasonable upper limit
        safe_batch = 8  # Fallback

        for _ in range(10):  # Max 10 iterations
            mid_batch = (min_batch + max_batch) // 2
            predicted_temp = self.predict_thermal_safety(task_type, mid_batch, duration_sec=1.0)

            if predicted_temp <= target_temp:
                # Can go higher
                safe_batch = mid_batch
                min_batch = mid_batch + 1
            else:
                # Too hot, go lower
                max_batch = mid_batch - 1

        logger.debug(
            f"Safe batch size for {task_type}: {safe_batch} "
            f"(predicted {self.predict_thermal_safety(task_type, safe_batch, 1.0):.1f}°C)"
        )

        return max(1, safe_batch)

    def predict_throttle_probability(self, task_type: str, batch_size: int) -> float:
        """Predict probability of thermal throttling.

        Uses sigmoid function: P(throttle) = 1 / (1 + e^(-k*(temp - 92)))

        Parameters
        ----------
        task_type : str
            Type of task
        batch_size : int
            Batch size

        Returns
        -------
        float
            Probability (0-1) of throttling occurring
        """
        predicted_temp = self.predict_thermal_safety(task_type, batch_size, 1.0)

        # Sigmoid centered at 92°C (throttle point)
        k = 0.5  # Steepness parameter
        throttle_point = self.THERMAL_THROTTLE_POINT

        try:
            exponent = -k * (predicted_temp - throttle_point)
            # Clamp to prevent overflow
            exponent = max(-100, min(100, exponent))
            probability = 1.0 / (1.0 + math.exp(exponent))
        except (OverflowError, ValueError):
            probability = 0.0 if predicted_temp < throttle_point else 1.0

        return max(0.0, min(1.0, probability))

    def estimate_performance_impact(self, throttle_percentage: float) -> float:
        """Estimate throughput penalty from throttling.

        Parameters
        ----------
        throttle_percentage : float
            Percentage of clock speed loss (0-100)

        Returns
        -------
        float
            Throughput multiplier (0.0-1.0)
        """
        # Linear impact: 50% clock loss = 50% throughput loss
        return max(0.0, 1.0 - throttle_percentage / 100.0)

    def get_confidence(self) -> float:
        """Get confidence of last prediction.

        Returns
        -------
        float
            Confidence from 0-1
        """
        if self._last_prediction is None:
            return 0.0
        return self._last_prediction[1]

    def get_stats(self) -> dict:
        """Get thermal analyzer statistics.

        Returns
        -------
        dict
            Statistics about thermal learning
        """
        stats = {
            "task_types_learned": list(self.history.keys()),
            "total_records": sum(len(v) for v in self.history.values()),
            "history_per_type": {k: len(v) for k, v in self.history.items()},
            "throttle_events": sum(
                1 for metrics_list in self.history.values() for m in metrics_list if m.throttle_detected
            ),
            "last_prediction": self._last_prediction,
        }

        # Add per-task-type thermal summary
        for task_type, metrics_list in self.history.items():
            if metrics_list:
                temps = [m.peak_gpu_temp for m in metrics_list]
                stats[f"{task_type}_avg_peak_temp_c"] = sum(temps) / len(temps)
                stats[f"{task_type}_max_peak_temp_c"] = max(temps)
                stats[f"{task_type}_min_peak_temp_c"] = min(temps)

        return stats

    async def learn_from_vault(self) -> None:
        """Query vault for historical thermal data.

        Phase 2 integration: Load past execution records and build
        thermal prediction model from real-world data.

        This is a placeholder for Phase 2 vault integration.
        """
        if not self.vault_client:
            logger.debug("No vault client configured, skipping thermal learning")
            return

        try:
            # TODO: Phase 2 - Query vault for thermal execution records
            # patterns = await self.vault_client.search(
            #     "thermal_execution",
            #     filters={"recorded_at": {\"$gte\": \"2026-02-01\"}}
            # )
            # for pattern in patterns:
            #     metrics = ThermalMetrics(**pattern)
            #     self.record_execution(metrics)
            logger.debug("Thermal vault learning not yet implemented (Phase 2)")
        except Exception as e:
            logger.debug(f"Thermal vault learning error: {e}")


def get_thermal_trend_analyzer(reset: bool = False) -> ThermalTrendAnalyzer:
    """Get or create singleton thermal trend analyzer.

    Parameters
    ----------
    reset : bool
        If True, create new instance (default: False)

    Returns
    -------
    ThermalTrendAnalyzer
        Singleton instance
    """
    global _analyzer_instance

    if reset or _analyzer_instance is None:
        _analyzer_instance = ThermalTrendAnalyzer()

    return _analyzer_instance


# Module-level singleton
_analyzer_instance: ThermalTrendAnalyzer | None = None


__all__ = [
    "ThermalMetrics",
    "ThermalTrendAnalyzer",
    "get_thermal_trend_analyzer",
]
