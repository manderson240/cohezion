"""Cost trend forecasting engine for predictive analytics.

Provides:
- Time-series forecasting (24h, 7d, 30d horizons)
- Exponential smoothing and trend analysis
- Confidence intervals for forecasts
- Anomaly scoring for unusual spend patterns
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import asdict, dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class Forecast:
    """Single cost forecast point."""

    timestamp: float
    horizon_hours: int
    predicted_cost_usd: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    confidence_pct: float  # Confidence level (e.g., 90, 95)
    method: str  # "exponential_smoothing", "linear_trend", "average"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ForecastSummary:
    """Summary of forecasts across time horizons."""

    timestamp: float
    forecast_24h_usd: float
    forecast_7d_usd: float
    forecast_30d_usd: float
    confidence_24h: float
    confidence_7d: float
    confidence_30d: float
    trend_direction: str  # "increasing", "decreasing", "stable"
    forecast_method: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AnomalyScore:
    """Anomaly detection result for spend pattern."""

    timestamp: float
    current_rate_usd_per_hour: float
    expected_rate_usd_per_hour: float
    deviation_pct: float
    anomaly_score: float  # 0-100, higher = more anomalous
    is_anomaly: bool  # True if deviation > threshold (default: >20%)
    anomaly_type: str  # "spike", "drop", "trend_change", "normal"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class ForecastEngine:
    """Cost trend forecasting with anomaly detection."""

    def __init__(
        self,
        alpha: float = 0.3,  # Exponential smoothing parameter
        anomaly_threshold_pct: float = 20.0,  # % deviation for anomaly
    ):
        """Initialize forecast engine.

        Args:
            alpha: Smoothing factor for exponential smoothing (0-1)
            anomaly_threshold_pct: Percentage deviation threshold for anomaly detection
        """
        self.alpha = alpha
        self.anomaly_threshold_pct = anomaly_threshold_pct

        # Historical data: (timestamp, cost_usd, hour_duration)
        self.history: list[tuple[float, float, float]] = []
        self.smoothed_level = 0.0
        self.smoothed_trend = 0.0

    def add_observation(
        self,
        timestamp: float,
        cost_usd: float,
        duration_hours: float = 1.0,
    ) -> None:
        """Add historical cost observation.

        Args:
            timestamp: Observation timestamp
            cost_usd: Cost in USD
            duration_hours: Duration of measurement in hours
        """
        self.history.append((timestamp, cost_usd, duration_hours))

        # Update smoothed estimates
        if len(self.history) == 1:
            self.smoothed_level = cost_usd / duration_hours
            self.smoothed_trend = 0.0
        else:
            # Simple exponential smoothing with trend
            previous_level = self.smoothed_level
            current_rate = cost_usd / duration_hours

            new_level = self.alpha * current_rate + (1 - self.alpha) * previous_level
            new_trend = self.alpha * (new_level - previous_level)

            self.smoothed_level = new_level
            self.smoothed_trend = new_trend

    def forecast(
        self,
        horizon_hours: int,
        confidence_pct: float = 90.0,
    ) -> Forecast | None:
        """Generate forecast for given horizon.

        Args:
            horizon_hours: Number of hours to forecast ahead
            confidence_pct: Confidence level for interval (90 or 95)

        Returns:
            Forecast object or None if insufficient data
        """
        if len(self.history) < 2:
            return None

        # Use exponential smoothing for forecast
        forecast_value = (
            self.smoothed_level + (horizon_hours / 24.0) * self.smoothed_trend
        )

        # Confidence interval (simplified: ±10-20% depending on horizon)
        interval_width = forecast_value * (0.10 + 0.05 * math.log(horizon_hours + 1))

        lower = max(0, forecast_value - interval_width)
        upper = forecast_value + interval_width

        return Forecast(
            timestamp=time.time(),
            horizon_hours=horizon_hours,
            predicted_cost_usd=forecast_value * horizon_hours,
            confidence_interval_lower=lower * horizon_hours,
            confidence_interval_upper=upper * horizon_hours,
            confidence_pct=confidence_pct,
            method="exponential_smoothing",
        )

    def forecast_summary(self) -> ForecastSummary | None:
        """Get forecasts for standard time horizons.

        Returns:
            ForecastSummary or None if insufficient data
        """
        if len(self.history) < 2:
            return None

        forecast_24h = self.forecast(24)
        forecast_7d = self.forecast(7 * 24)
        forecast_30d = self.forecast(30 * 24)

        if not forecast_24h:
            return None

        # Determine trend
        trend_direction = "stable"
        if self.smoothed_trend > 0.01:
            trend_direction = "increasing"
        elif self.smoothed_trend < -0.01:
            trend_direction = "decreasing"

        return ForecastSummary(
            timestamp=time.time(),
            forecast_24h_usd=forecast_24h.predicted_cost_usd,
            forecast_7d_usd=forecast_7d.predicted_cost_usd if forecast_7d else 0.0,
            forecast_30d_usd=forecast_30d.predicted_cost_usd if forecast_30d else 0.0,
            confidence_24h=forecast_24h.confidence_pct,
            confidence_7d=forecast_7d.confidence_pct if forecast_7d else 90.0,
            confidence_30d=forecast_30d.confidence_pct if forecast_30d else 90.0,
            trend_direction=trend_direction,
            forecast_method="exponential_smoothing",
        )

    def detect_anomaly(
        self,
        current_rate_usd_per_hour: float,
    ) -> AnomalyScore:
        """Detect anomalies in current spend rate.

        Args:
            current_rate_usd_per_hour: Current spend rate in USD/hour

        Returns:
            AnomalyScore with anomaly detection result
        """
        expected_rate = self.smoothed_level
        deviation = abs(current_rate_usd_per_hour - expected_rate)
        deviation_pct = (deviation / expected_rate * 100) if expected_rate > 0 else 0

        # Anomaly scoring: 0-100
        # 0 = no deviation, 50 = 20% threshold, 100 = 50% deviation
        anomaly_score = min(100, (deviation_pct / 50) * 100)

        is_anomaly = deviation_pct > self.anomaly_threshold_pct

        # Determine anomaly type
        anomaly_type = "normal"
        if is_anomaly:
            anomaly_type = "spike" if current_rate_usd_per_hour > expected_rate else "drop"

        return AnomalyScore(
            timestamp=time.time(),
            current_rate_usd_per_hour=current_rate_usd_per_hour,
            expected_rate_usd_per_hour=expected_rate,
            deviation_pct=deviation_pct,
            anomaly_score=anomaly_score,
            is_anomaly=is_anomaly,
            anomaly_type=anomaly_type,
        )

    def get_history_stats(self) -> dict[str, float]:
        """Get statistics from historical data.

        Returns:
            Dictionary with min, max, mean, and trend stats
        """
        if not self.history:
            return {}

        costs = [cost for _, cost, duration in self.history]
        rates = [cost / duration for _, cost, duration in self.history]

        return {
            "min_rate_usd_per_hour": min(rates) if rates else 0,
            "max_rate_usd_per_hour": max(rates) if rates else 0,
            "mean_rate_usd_per_hour": sum(rates) / len(rates) if rates else 0,
            "total_cost_usd": sum(costs),
            "observation_count": len(self.history),
            "smoothed_level_usd_per_hour": self.smoothed_level,
            "smoothed_trend_usd_per_hour": self.smoothed_trend,
        }

    def reset(self) -> None:
        """Reset forecast engine (testing only)."""
        self.history.clear()
        self.smoothed_level = 0.0
        self.smoothed_trend = 0.0


_instance: ForecastEngine | None = None


def get_forecast_engine() -> ForecastEngine:
    """Get or create singleton forecast engine."""
    global _instance
    if _instance is None:
        _instance = ForecastEngine()
    return _instance


def reset_forecast_engine() -> None:
    """Reset forecast engine singleton (testing only)."""
    global _instance
    _instance = None
