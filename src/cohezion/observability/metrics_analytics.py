"""Metrics analytics and trend tracking for observability dashboard.

Provides:
- Time-series analysis of metrics
- Anomaly detection in performance
- Trend identification
- Health scoring
- Dashboard report generation
"""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cohezion.observability.unified_metrics import InferenceMetrics


logger = logging.getLogger(__name__)


@dataclass
class MetricsTrend:
    """Trend data for a metric over time."""

    metric_name: str
    current_value: float
    previous_value: float
    change_percent: float
    trend_direction: str  # "up", "down", "stable"
    anomaly_detected: bool = False
    anomaly_reason: str = ""


@dataclass
class PerformanceReport:
    """Comprehensive performance report."""

    timestamp: datetime
    cache_performance: dict[str, Any]
    token_efficiency: dict[str, Any]
    guardrail_performance: dict[str, Any]
    resource_performance: dict[str, Any]
    overall_health_score: float  # 0.0-1.0
    recommendations: list[str] = field(default_factory=list)


class MetricsAnalytics:
    """Analyze metrics and generate insights for dashboard."""

    def __init__(self, window_size: int = 100):
        """Initialize analytics.

        Args:
            window_size: Number of historical records to maintain for trend analysis
        """
        self.window_size = window_size
        self.history: list[InferenceMetrics] = []
        self.thresholds = {
            "cache_hit_rate_low": 70,  # Below 70% is concerning
            "cache_hit_rate_high": 95,  # Above 95% is excellent
            "guardrail_block_rate_high": 5,  # >5% blocks is concerning
            "token_efficiency_low": 85,  # tok/sec baseline
            "memory_peak_critical": 110.0,  # GB, critical threshold
        }

    def add_metrics(self, metrics: InferenceMetrics) -> None:
        """Add metrics snapshot to history.

        Args:
            metrics: InferenceMetrics snapshot
        """
        self.history.append(metrics)
        # Keep only last window_size entries
        if len(self.history) > self.window_size:
            self.history = self.history[-self.window_size :]

    def get_cache_analytics(self) -> dict[str, Any]:
        """Analyze cache performance.

        Returns:
            Dictionary with cache metrics and insights
        """
        if not self.history:
            return {
                "l1_hit_rate_avg": 0.0,
                "l2_hit_rate_avg": 0.0,
                "l3_hit_rate_avg": 0.0,
                "total_hit_rate_avg": 0.0,
                "cache_health": "no_data",
            }

        l1_rates = [m.l1_cache_hit_rate for m in self.history if m.cache_l1_hits > 0]
        l2_rates = [m.l2_cache_hit_rate for m in self.history if m.cache_l2_hits > 0]
        l3_rates = [
            m.cache_l3_hits / (m.cache_l3_hits + m.cache_misses + 1) * 100 for m in self.history
        ]
        total_rates = [m.total_cache_hit_rate for m in self.history]

        avg_l1 = statistics.mean(l1_rates) if l1_rates else 0.0
        avg_l2 = statistics.mean(l2_rates) if l2_rates else 0.0
        avg_l3 = statistics.mean(l3_rates) if l3_rates else 0.0
        avg_total = statistics.mean(total_rates) if total_rates else 0.0

        # Determine cache health
        if avg_total < self.thresholds["cache_hit_rate_low"]:
            health = "poor"
        elif avg_total < 0.85:
            health = "fair"
        elif avg_total < self.thresholds["cache_hit_rate_high"]:
            health = "good"
        else:
            health = "excellent"

        return {
            "l1_hit_rate_avg": round(avg_l1, 2),
            "l2_hit_rate_avg": round(avg_l2, 2),
            "l3_hit_rate_avg": round(avg_l3, 2),
            "total_hit_rate_avg": round(avg_total, 2),
            "cache_health": health,
            "recommendation": self._cache_recommendation(avg_total, avg_l2),
        }

    def get_token_efficiency_analytics(self) -> dict[str, Any]:
        """Analyze token efficiency metrics.

        Returns:
            Dictionary with token efficiency insights
        """
        if not self.history:
            return {
                "avg_tokens_per_op": 0,
                "total_tokens": 0,
                "avg_duration_ms": 0.0,
                "efficiency_health": "no_data",
            }

        total_tokens = sum(m.total_tokens for m in self.history)
        total_duration = sum(m.total_duration_ms for m in self.history)
        total_ops = len(self.history)

        if total_duration > 0:
            avg_tokens_per_op = total_tokens / total_ops
            avg_duration = total_duration / total_ops
            tokens_per_sec = total_tokens / (total_duration / 1000)
        else:
            avg_tokens_per_op = 0
            avg_duration = 0.0
            tokens_per_sec = 0.0

        # Determine efficiency health
        if tokens_per_sec < self.thresholds["token_efficiency_low"]:
            health = "poor"
        elif tokens_per_sec < 120:
            health = "fair"
        elif tokens_per_sec < 150:
            health = "good"
        else:
            health = "excellent"

        return {
            "avg_tokens_per_op": round(avg_tokens_per_op, 1),
            "total_tokens": total_tokens,
            "avg_duration_ms": round(avg_duration, 2),
            "tokens_per_sec": round(tokens_per_sec, 2),
            "efficiency_health": health,
            "target_tokens_per_sec": 155,
            "efficiency_gap": round(155 - tokens_per_sec, 2),
        }

    def get_guardrail_analytics(self) -> dict[str, Any]:
        """Analyze guardrail performance.

        Returns:
            Dictionary with guardrail metrics and insights
        """
        if not self.history:
            return {
                "total_checks": 0,
                "total_blocks": 0,
                "block_rate": 0.0,
                "guardrail_health": "no_data",
            }

        total_checks = sum(m.guardrail_checks for m in self.history)
        total_blocks = sum(m.guardrail_blocks for m in self.history)
        total_sanitizations = sum(m.guardrail_sanitizations for m in self.history)
        avg_latency = (
            statistics.mean(
                [m.guardrail_latency_ms for m in self.history if m.guardrail_latency_ms > 0]
            )
            if any(m.guardrail_latency_ms > 0 for m in self.history)
            else 0.0
        )

        block_rate = (total_blocks / total_checks * 100) if total_checks > 0 else 0.0

        # Determine guardrail health
        if block_rate > self.thresholds["guardrail_block_rate_high"]:
            health = "warning"  # High block rate could indicate false positives
        else:
            health = "good"

        return {
            "total_checks": total_checks,
            "total_blocks": total_blocks,
            "total_sanitizations": total_sanitizations,
            "block_rate_percent": round(block_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "guardrail_health": health,
            "recommendation": self._guardrail_recommendation(block_rate),
        }

    def get_resource_analytics(self) -> dict[str, Any]:
        """Analyze resource usage.

        Returns:
            Dictionary with resource metrics
        """
        if not self.history:
            return {
                "peak_memory_gb": 0.0,
                "avg_concurrency_waits": 0,
                "resource_health": "no_data",
            }

        peak_memory = max(m.peak_memory_gb for m in self.history)
        total_waits = sum(m.concurrency_waits for m in self.history)
        avg_waits = total_waits / len(self.history) if self.history else 0

        # Determine resource health
        if peak_memory > self.thresholds["memory_peak_critical"]:
            health = "critical"
        elif peak_memory > 100.0:
            health = "warning"
        else:
            health = "good"

        return {
            "peak_memory_gb": round(peak_memory, 2),
            "avg_concurrency_waits": round(avg_waits, 2),
            "resource_health": health,
            "memory_utilization_percent": round((peak_memory / 128.0) * 100, 1),
        }

    def compute_health_score(self) -> float:
        """Compute overall system health score (0.0-1.0).

        Returns:
            Health score combining all metrics
        """
        cache_stats = self.get_cache_analytics()
        token_stats = self.get_token_efficiency_analytics()
        guardrail_stats = self.get_guardrail_analytics()
        resource_stats = self.get_resource_analytics()

        # Weight each component
        cache_score = (cache_stats["total_hit_rate_avg"] / 100.0) * 0.35
        token_score = min((token_stats["tokens_per_sec"] / 155.0), 1.0) * 0.35
        guardrail_score = (1.0 - min(guardrail_stats["block_rate_percent"] / 10.0, 1.0)) * 0.15
        resource_score = (
            1.0 - (min(resource_stats["memory_utilization_percent"] / 100.0, 1.0))
        ) * 0.15

        total_score = cache_score + token_score + guardrail_score + resource_score
        return min(max(total_score, 0.0), 1.0)

    def generate_dashboard_report(self) -> PerformanceReport:
        """Generate comprehensive dashboard report.

        Returns:
            PerformanceReport with all metrics and recommendations
        """
        cache_analytics = self.get_cache_analytics()
        token_analytics = self.get_token_efficiency_analytics()
        guardrail_analytics = self.get_guardrail_analytics()
        resource_analytics = self.get_resource_analytics()
        health_score = self.compute_health_score()

        recommendations = self._generate_recommendations(
            cache_analytics, token_analytics, guardrail_analytics, resource_analytics
        )

        return PerformanceReport(
            timestamp=datetime.now(),
            cache_performance=cache_analytics,
            token_efficiency=token_analytics,
            guardrail_performance=guardrail_analytics,
            resource_performance=resource_analytics,
            overall_health_score=health_score,
            recommendations=recommendations,
        )

    @staticmethod
    def _cache_recommendation(total_rate: float, l2_rate: float) -> str:
        """Generate cache-specific recommendation.

        Args:
            total_rate: Overall cache hit rate
            l2_rate: L2 cache hit rate

        Returns:
            Recommendation text
        """
        if total_rate < 0.70:
            return "Cache hit rate is low. Consider warming cache or adjusting thresholds."
        elif l2_rate < 20:
            return "L2 semantic cache underutilized. Adjust similarity threshold or check query patterns."
        else:
            return "Cache performance is excellent. Continue current configuration."

    @staticmethod
    def _guardrail_recommendation(block_rate: float) -> str:
        """Generate guardrail-specific recommendation.

        Args:
            block_rate: Percentage of requests blocked

        Returns:
            Recommendation text
        """
        if block_rate > 5:
            return "High block rate detected. Review guardrail thresholds for false positives."
        else:
            return "Guardrail block rate is healthy."

    @staticmethod
    def _generate_recommendations(
        cache_analytics: dict[str, Any],
        token_analytics: dict[str, Any],
        guardrail_analytics: dict[str, Any],
        resource_analytics: dict[str, Any],
    ) -> list[str]:
        """Generate actionable recommendations.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Cache recommendations
        if cache_analytics["total_hit_rate_avg"] < 70:
            recommendations.append(
                "🔴 Cache hit rate below target. Enable cache warming or adjust thresholds."
            )
        if cache_analytics["l2_hit_rate_avg"] < 20:
            recommendations.append(
                "🟡 L2 semantic cache underutilized. Consider relaxing similarity threshold."
            )

        # Token efficiency recommendations
        efficiency_gap = token_analytics["efficiency_gap"]
        if efficiency_gap > 20:
            recommendations.append(
                f"🟡 Token efficiency {efficiency_gap:.0f} tok/sec below target. Focus on semantic cache optimization."
            )

        # Guardrail recommendations
        if guardrail_analytics["block_rate_percent"] > 5:
            recommendations.append(
                "🟡 High guardrail block rate. Review thresholds to reduce false positives."
            )

        # Resource recommendations
        if resource_analytics["resource_health"] == "critical":
            recommendations.append(
                "🔴 CRITICAL: Memory usage critical. Consider reducing batch sizes."
            )
        if resource_analytics["avg_concurrency_waits"] > 10:
            recommendations.append(
                "🟡 High concurrency waits detected. Consider increasing concurrency limits."
            )

        # Positive feedback
        if not recommendations:
            recommendations.append("✅ All systems operating within healthy parameters.")

        return recommendations

    def get_trend(self, metric_name: str, window: int = 10) -> MetricsTrend | None:
        """Get trend for a specific metric.

        Args:
            metric_name: Name of metric (e.g., "total_cache_hit_rate")
            window: Number of recent records to use for trend

        Returns:
            MetricsTrend or None if insufficient data
        """
        if len(self.history) < 2:
            return None

        recent = self.history[-window:] if len(self.history) >= window else self.history

        if metric_name == "total_cache_hit_rate":
            values = [m.total_cache_hit_rate for m in recent]
        elif metric_name == "l2_cache_hit_rate":
            values = [m.l2_cache_hit_rate for m in recent]
        elif metric_name == "guardrail_block_rate":
            values = [m.guardrail_block_rate for m in recent]
        else:
            return None

        if len(values) < 2:
            return None

        current = values[-1]
        previous = values[-2]
        change = current - previous

        change_percent = change / previous * 100 if previous != 0 else 0.0

        # Determine trend direction
        if change > 1:
            direction = "up"
        elif change < -1:
            direction = "down"
        else:
            direction = "stable"

        # Detect anomalies (sudden spikes/drops)
        if len(values) >= 3:
            avg_prev = statistics.mean(values[:-1])
            if previous != 0 and abs(current - avg_prev) / avg_prev > 0.3:
                anomaly_detected = True
                anomaly_reason = f"Sudden {direction} in {metric_name}"
            else:
                anomaly_detected = False
                anomaly_reason = ""
        else:
            anomaly_detected = False
            anomaly_reason = ""

        return MetricsTrend(
            metric_name=metric_name,
            current_value=current,
            previous_value=previous,
            change_percent=change_percent,
            trend_direction=direction,
            anomaly_detected=anomaly_detected,
            anomaly_reason=anomaly_reason,
        )
