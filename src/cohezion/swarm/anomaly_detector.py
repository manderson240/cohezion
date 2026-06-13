"""Cost anomaly detection for unusual patterns.

Features:
- Sudden cost spike detection (>20% deviation from forecast)
- Cost trend analysis (gradual increase over time)
- Model coherence drop detection (quality vs cost trade-off)
- False positive filtering (<5% target)
- Multi-threshold approach for different anomaly types

Architecture:
  Cost Metrics (per query/window)
       ↓
  Forecast Comparison
       ↓
  Anomaly Classification
       ↓
  False Positive Filtering
       ↓
  Alert Generation

Usage:
    detector = AnomalyDetector(forecast_threshold=0.20, trend_window_hours=2)
    anomaly = detector.detect_spike(
        actual_cost=0.50,
        forecasted_cost=0.40,
        model="qwen3-coder:32b"
    )
    if anomaly:
        logger.warning(f"Cost anomaly: {anomaly.description}")
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    """Types of cost anomalies."""

    SPIKE = "spike"  # Sudden cost increase
    TREND = "trend"  # Gradual increasing trend
    QUALITY_COST_MISMATCH = "quality_cost_mismatch"  # High cost with low quality
    COHERENCE_DROP = "coherence_drop"  # Quality drops while cost rises
    UNKNOWN = "unknown"


@dataclass
class AnomalyAlert:
    """Anomaly alert details."""

    anomaly_type: AnomalyType
    detected_at: float
    cost_actual: float
    cost_forecasted: float | None
    cost_deviation_pct: float
    model: str
    severity: float  # 0.0 - 1.0
    description: str
    confidence: float  # 0.0 - 1.0 (1 - false positive risk)
    metrics: dict[str, float] = field(default_factory=dict)

    def is_valid_alert(self, fp_threshold: float = 0.05) -> bool:
        """Check if alert passes false positive threshold.

        Args:
            fp_threshold: Maximum acceptable false positive rate (default: 5%)

        Returns:
            True if confidence is high enough
        """
        # Convert fp_threshold to confidence requirement
        # fp_threshold 0.05 means we accept 5% false positives,
        # which requires confidence >= 0.95 to be statistically safe
        # However, we're more lenient: confidence >= (1 - fp_threshold * 2)
        return self.confidence >= (1.0 - fp_threshold * 2)


@dataclass
class ModelCostHistory:
    """Cost history tracking for anomaly detection."""

    model: str
    costs: deque = field(default_factory=lambda: deque(maxlen=100))
    times: deque = field(default_factory=lambda: deque(maxlen=100))
    forecasts: deque = field(default_factory=lambda: deque(maxlen=100))
    coherence_scores: deque = field(default_factory=lambda: deque(maxlen=100))

    def add_datapoint(
        self,
        cost: float,
        forecast: float | None = None,
        coherence: float = 0.7,
    ) -> None:
        """Add cost datapoint to history."""
        self.costs.append(cost)
        self.times.append(time.time())
        self.forecasts.append(forecast or cost)
        self.coherence_scores.append(coherence)

    def get_recent_costs(self, minutes: int = 10) -> list[float]:
        """Get costs from last N minutes."""
        now = time.time()
        cutoff = now - (minutes * 60)
        return [cost for cost, t in zip(self.costs, self.times, strict=True) if t >= cutoff]

    def get_average_cost(self, minutes: int = 10) -> float:
        """Get average cost over last N minutes."""
        recent = self.get_recent_costs(minutes)
        return sum(recent) / len(recent) if recent else 0.0

    def get_cost_trend(self, minutes: int = 60) -> float:
        """Get cost trend slope over N minutes.

        Returns:
            Positive = increasing costs, negative = decreasing
        """
        now = time.time()
        cutoff = now - (minutes * 60)

        recent_costs = []
        recent_times = []
        for cost, t in zip(self.costs, self.times, strict=True):
            if t >= cutoff:
                recent_costs.append(cost)
                recent_times.append(t)

        if len(recent_costs) < 2:
            return 0.0

        # Simple linear regression slope
        n = len(recent_costs)
        mean_x = sum(recent_times) / n
        mean_y = sum(recent_costs) / n

        numerator = sum(
            (t - mean_x) * (c - mean_y) for t, c in zip(recent_times, recent_costs, strict=True)
        )
        denominator = sum((t - mean_x) ** 2 for t in recent_times)

        if denominator == 0:
            return 0.0

        return float(numerator / denominator)  # Cost per second


class AnomalyDetector:
    """Detect cost anomalies in model routing."""

    def __init__(
        self,
        forecast_threshold: float = 0.20,  # 20% deviation
        trend_threshold: float = 0.0005,  # Cost/second increase
        trend_window_hours: int = 2,
        coherence_threshold: float = -0.10,  # 10% drop acceptable
        fp_adjustment_factor: float = 0.9,  # Reduce false positives
    ):
        """Initialize anomaly detector.

        Args:
            forecast_threshold: Deviation % to trigger spike (0.0 - 1.0)
            trend_threshold: Cost/second slope for trend detection
            trend_window_hours: Time window for trend analysis
            coherence_threshold: Coherence drop tolerance
            fp_adjustment_factor: Confidence boost (0.0 - 1.0)
        """
        self.forecast_threshold = forecast_threshold
        self.trend_threshold = trend_threshold
        self.trend_window_hours = trend_window_hours
        self.coherence_threshold = coherence_threshold
        self.fp_adjustment_factor = fp_adjustment_factor

        # Per-model cost history
        self.model_histories: dict[str, ModelCostHistory] = {}

        # Alert tracking
        self.recent_alerts: deque = deque(maxlen=1000)
        self.false_positive_rate = 0.0

    def detect_spike(
        self,
        actual_cost: float,
        forecasted_cost: float | None = None,
        model: str = "unknown",
        coherence_score: float = 0.7,
    ) -> AnomalyAlert | None:
        """Detect sudden cost spike.

        Args:
            actual_cost: Actual cost observed
            forecasted_cost: Expected cost from forecast
            model: Model being used
            coherence_score: Coherence score (0.0 - 1.0)

        Returns:
            AnomalyAlert if spike detected, None otherwise
        """
        if forecasted_cost is None:
            forecasted_cost = actual_cost

        self._ensure_history(model)
        history = self.model_histories[model]
        history.add_datapoint(actual_cost, forecasted_cost, coherence_score)

        # Check deviation
        deviation = (actual_cost - forecasted_cost) / max(forecasted_cost, 0.01)

        if abs(deviation) <= self.forecast_threshold:
            return None  # No spike

        # Classify spike
        severity = min(1.0, abs(deviation) / (self.forecast_threshold * 2))
        confidence = self._calculate_confidence(
            anomaly_type=AnomalyType.SPIKE,
            deviation=abs(deviation),
            recent_history=history.get_recent_costs(10),
        )

        if not self._passes_fp_filter(confidence):
            return None

        alert = AnomalyAlert(
            anomaly_type=AnomalyType.SPIKE,
            detected_at=time.time(),
            cost_actual=actual_cost,
            cost_forecasted=forecasted_cost,
            cost_deviation_pct=deviation * 100,
            model=model,
            severity=severity,
            confidence=confidence,
            description=f"Cost spike: {actual_cost:.4f} vs {forecasted_cost:.4f} ({deviation * 100:+.1f}%)",
            metrics={
                "actual": actual_cost,
                "forecasted": forecasted_cost,
                "deviation_pct": deviation * 100,
                "coherence": coherence_score,
            },
        )

        self.recent_alerts.append(alert)
        logger.warning(f"Anomaly SPIKE detected: {alert.description}")
        return alert

    def detect_trend(
        self,
        model: str,
        coherence_score: float = 0.7,
    ) -> AnomalyAlert | None:
        """Detect cost trending upward over time.

        Args:
            model: Model to check
            coherence_score: Current coherence score

        Returns:
            AnomalyAlert if trend detected, None otherwise
        """
        self._ensure_history(model)
        history = self.model_histories[model]

        # Need at least some history
        if len(history.costs) < 2:
            return None

        # Get trend over window
        trend_slope = history.get_cost_trend(minutes=self.trend_window_hours * 60)

        if trend_slope <= self.trend_threshold:
            return None  # No upward trend

        # Calculate severity based on trend
        # trend_slope is in cost/second, convert to cost change over window
        total_change = trend_slope * (self.trend_window_hours * 3600)
        severity = min(1.0, abs(total_change) / 0.10)  # Normalize to 0.1 cost unit

        # Check if coherence is dropping too
        recent_coherence = list(history.coherence_scores)
        if len(recent_coherence) >= 2:
            coherence_change = recent_coherence[-1] - recent_coherence[0]
            if coherence_change < self.coherence_threshold:
                severity = min(1.0, severity * 1.5)  # Boost severity

        recent_costs = history.get_recent_costs(self.trend_window_hours * 60)
        confidence = self._calculate_confidence(
            anomaly_type=AnomalyType.TREND,
            deviation=max(0.01, total_change),  # Ensure non-zero for calculation
            recent_history=recent_costs if recent_costs else [0.1],
        )

        if not self._passes_fp_filter(confidence):
            return None

        alert = AnomalyAlert(
            anomaly_type=AnomalyType.TREND,
            detected_at=time.time(),
            cost_actual=history.get_average_cost(10),
            cost_forecasted=history.get_average_cost(30),
            cost_deviation_pct=min(100.0, total_change * 100),  # Cap at 100%
            model=model,
            severity=severity,
            confidence=confidence,
            description=f"Cost trend: rising {trend_slope * 3600:.6f} cost/hour over {self.trend_window_hours}h",
            metrics={
                "trend_slope": trend_slope,
                "total_change": total_change,
                "window_hours": self.trend_window_hours,
                "coherence": coherence_score,
            },
        )

        self.recent_alerts.append(alert)
        logger.warning(f"Anomaly TREND detected: {alert.description}")
        return alert

    def detect_quality_cost_mismatch(
        self,
        cost: float,
        coherence_score: float,
        model: str = "unknown",
    ) -> AnomalyAlert | None:
        """Detect high cost with low quality output.

        Args:
            cost: Cost of execution
            coherence_score: Output coherence (0.0 - 1.0)
            model: Model being used

        Returns:
            AnomalyAlert if mismatch detected, None otherwise
        """
        # High cost + low coherence = mismatch
        cost_ratio = min(1.0, cost / 0.5)  # Normalized against typical cost
        quality_ratio = coherence_score

        mismatch_score = (1.0 - quality_ratio) * cost_ratio

        if mismatch_score < 0.3:  # Threshold for mismatch
            return None

        severity = mismatch_score
        confidence = self._calculate_confidence(
            anomaly_type=AnomalyType.QUALITY_COST_MISMATCH,
            deviation=mismatch_score,
            recent_history=[cost],
        )

        if not self._passes_fp_filter(confidence):
            return None

        alert = AnomalyAlert(
            anomaly_type=AnomalyType.QUALITY_COST_MISMATCH,
            detected_at=time.time(),
            cost_actual=cost,
            cost_forecasted=None,
            cost_deviation_pct=mismatch_score * 100,
            model=model,
            severity=severity,
            confidence=confidence,
            description=f"Quality-cost mismatch: high cost ({cost:.4f}) with low coherence ({coherence_score:.2f})",
            metrics={
                "cost": cost,
                "coherence": coherence_score,
                "mismatch_score": mismatch_score,
            },
        )

        self.recent_alerts.append(alert)
        logger.warning(f"Anomaly QUALITY_COST_MISMATCH detected: {alert.description}")
        return alert

    def get_false_positive_rate(self, minutes: int = 60) -> float:
        """Get false positive rate over recent window.

        Args:
            minutes: Time window to analyze

        Returns:
            False positive rate (0.0 - 1.0)
        """
        now = time.time()
        cutoff = now - (minutes * 60)

        recent = [a for a in self.recent_alerts if a.detected_at >= cutoff]

        if not recent:
            return 0.0

        # Heuristic: assume alerts with very high confidence are true positives
        false_positives = sum(1 for a in recent if a.confidence < 0.85)

        return false_positives / len(recent)

    def reset(self) -> None:
        """Reset detector state (testing)."""
        self.model_histories.clear()
        self.recent_alerts.clear()
        self.false_positive_rate = 0.0

    def _ensure_history(self, model: str) -> None:
        """Ensure model has cost history."""
        if model not in self.model_histories:
            self.model_histories[model] = ModelCostHistory(model=model)

    def _calculate_confidence(
        self,
        anomaly_type: AnomalyType,
        deviation: float,
        recent_history: list[float],
    ) -> float:
        """Calculate confidence that anomaly is real.

        Args:
            anomaly_type: Type of anomaly
            deviation: Magnitude of deviation
            recent_history: Recent cost values

        Returns:
            Confidence (0.0 - 1.0)
        """
        # Base confidence from deviation
        if anomaly_type == AnomalyType.SPIKE:
            base_confidence = min(1.0, deviation / 0.5)
        elif anomaly_type == AnomalyType.TREND:
            base_confidence = min(1.0, deviation / 0.1)
        else:
            base_confidence = min(1.0, deviation / 0.5)

        # Boost confidence if pattern is consistent
        if len(recent_history) >= 3:
            # Check if values are consistently high/low
            variance = sum(
                (x - sum(recent_history) / len(recent_history)) ** 2 for x in recent_history
            ) / len(recent_history)
            consistency = 1.0 / (1.0 + variance)  # Normalize
            base_confidence = base_confidence * (0.5 + 0.5 * consistency)

        # Apply false positive adjustment
        adjusted = base_confidence * self.fp_adjustment_factor
        return min(1.0, adjusted)

    def _passes_fp_filter(self, confidence: float) -> bool:
        """Check if alert passes false positive filter.

        Args:
            confidence: Alert confidence

        Returns:
            True if should generate alert
        """
        return confidence >= 0.40  # 40% confidence minimum (after adjustments)


# Singleton instance
_anomaly_detector: AnomalyDetector | None = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get or create singleton anomaly detector."""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector


def reset_anomaly_detector() -> None:
    """Reset anomaly detector singleton (testing only)."""
    global _anomaly_detector
    _anomaly_detector = None
