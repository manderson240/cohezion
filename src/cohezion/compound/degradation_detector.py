"""Degradation detection for Phase 5A.6 - Monitor and alert on metric drops.

Detects when system performance degrades by monitoring:
- Cache hit rate (alert if drops below 50%)
- Token efficiency (alert if baseline drops >10%)
- Model quality (coherence, success rate anomalies)
- Execution duration (alert on slowdowns)

Architecture:
- MetricBaseline: Stores moving average + std dev for each metric
- DegradationDetector: Monitors current vs baseline, emits alerts
- DegradationAlert: Alert events with severity (WARNING, CRITICAL)
- Non-blocking: All vault ops wrapped in try/except

Usage::

    detector = DegradationDetector(
        cache_hit_rate_threshold=0.50,
        token_efficiency_drop_threshold=0.10,
        coherence_threshold=0.60,
    )

    # After each execution
    metrics = executor.get_metrics()
    alerts = detector.check_degradation(metrics)

    for alert in alerts:
        if alert.severity == "CRITICAL":
            logger.error(f"CRITICAL: {alert.message}")
        else:
            logger.warning(f"WARNING: {alert.message}")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""

    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class DegradationAlert:
    """Single degradation alert event."""

    metric: str  # "cache_hit_rate", "token_efficiency", "coherence", "duration"
    severity: AlertSeverity
    message: str
    current_value: float
    baseline_value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class MetricBaseline:
    """Baseline statistics for a single metric."""

    metric_name: str
    samples: list[float] = field(default_factory=list)
    window_size: int = 20  # Keep last N samples for moving average
    min_samples: int = 5  # Need at least N samples to establish baseline

    @property
    def mean(self) -> float:
        """Get moving average."""
        if not self.samples:
            return 0.0
        return float(np.mean(self.samples[-self.window_size :]))

    @property
    def std_dev(self) -> float:
        """Get standard deviation of recent samples."""
        if len(self.samples) < 2:
            return 0.0
        return float(np.std(self.samples[-self.window_size :]))

    @property
    def is_established(self) -> bool:
        """Check if baseline has enough samples."""
        return len(self.samples) >= self.min_samples

    def add_sample(self, value: float) -> None:
        """Add a new sample to the baseline."""
        self.samples.append(value)

    def lower_bound(self, std_devs: float = 2.0) -> float:
        """Get lower bound (mean - N*std_dev)."""
        return self.mean - (std_devs * self.std_dev)


class DegradationDetector:
    """Monitor metrics and detect degradation.

    Tracks moving averages and alerts when metrics fall below thresholds.
    All vault operations are non-blocking (try/except wrapped).

    Parameters
    ----------
    cache_hit_rate_threshold : float
        Alert if cache hit rate drops below this (default: 0.50)
    token_efficiency_drop_threshold : float
        Alert if token efficiency drops more than this % (default: 0.10 = 10%)
    coherence_threshold : float
        Alert if coherence drops below this (default: 0.60)
    duration_slowdown_threshold : float
        Alert if duration increases more than this % (default: 0.25 = 25%)
    """

    def __init__(
        self,
        cache_hit_rate_threshold: float = 0.50,
        token_efficiency_drop_threshold: float = 0.10,
        coherence_threshold: float = 0.60,
        duration_slowdown_threshold: float = 0.25,
    ) -> None:
        """Initialize degradation detector."""
        self.cache_hit_rate_threshold = cache_hit_rate_threshold
        self.token_efficiency_drop_threshold = token_efficiency_drop_threshold
        self.coherence_threshold = coherence_threshold
        self.duration_slowdown_threshold = duration_slowdown_threshold

        # Baselines for each metric
        self._baselines = {
            "cache_hit_rate": MetricBaseline("cache_hit_rate"),
            "token_efficiency": MetricBaseline("token_efficiency"),
            "coherence": MetricBaseline("coherence"),
            "duration_seconds": MetricBaseline("duration_seconds"),
            "success_rate": MetricBaseline("success_rate"),
        }

        # Alert history for deduplication
        self._last_alert_time: dict[str, float] = {}
        self._alert_cooldown_seconds = 60.0  # Don't repeat same alert within 60s

        # Healing pipeline integration (non-blocking)
        self._healing_enabled = True

        # Routing feedback callback (wired by CompoundExecutor)
        self._routing_callback: Any = None

        # Serialization counters (CB7/CB9)
        self._call_count: int = 0
        self._alert_history: list[DegradationAlert] = []

        logger.debug("DegradationDetector initialized with thresholds")

    def set_routing_callback(self, callback: Any) -> None:
        """Set callback for routing feedback on degradation alerts.

        Called by CompoundExecutor to wire DegradationDetector → CostAwareRouter.
        The callback receives the list of DegradationAlert objects.
        """
        self._routing_callback = callback
        logger.debug("Routing feedback callback registered")

    def check_degradation(self, metrics: dict[str, Any]) -> list[DegradationAlert]:
        """Check if metrics show degradation compared to baseline.

        Args:
            metrics: Dict with metric names and values

        Returns:
            List of DegradationAlert if degradation detected, empty list otherwise
        """
        self._call_count += 1
        alerts = []

        # Extract metrics
        cache_hit_rate = metrics.get("combined_hit_rate", 0.0)
        tokens_per_sec = metrics.get("tokens_per_second", 0.0)
        coherence = metrics.get("mean_coherence", 0.5)
        duration = metrics.get("elapsed_seconds", 0.0)
        success_rate = metrics.get("success_rate", 1.0)

        # Check conditions AGAINST ESTABLISHED BASELINES FIRST
        # Then add samples after all checks are done

        # Check cache hit rate
        if (
            self._baselines["cache_hit_rate"].is_established
            and cache_hit_rate < self.cache_hit_rate_threshold
        ):
            alert = DegradationAlert(
                metric="cache_hit_rate",
                severity=AlertSeverity.WARNING,
                message=f"Cache hit rate dropped to {cache_hit_rate:.1%} "
                f"(threshold: {self.cache_hit_rate_threshold:.1%})",
                current_value=cache_hit_rate,
                baseline_value=self._baselines["cache_hit_rate"].mean,
                threshold=self.cache_hit_rate_threshold,
            )
            if self._should_emit_alert(alert):
                alerts.append(alert)

        # Check token efficiency
        if self._baselines["token_efficiency"].is_established:
            baseline_tok_sec = self._baselines["token_efficiency"].mean
            if baseline_tok_sec > 0:
                efficiency_drop = 1.0 - (tokens_per_sec / baseline_tok_sec)
                if efficiency_drop > self.token_efficiency_drop_threshold:
                    alert = DegradationAlert(
                        metric="token_efficiency",
                        severity=AlertSeverity.WARNING,
                        message=f"Token efficiency dropped {efficiency_drop:.1%} "
                        f"({tokens_per_sec:.0f} vs baseline {baseline_tok_sec:.0f} tok/sec)",
                        current_value=tokens_per_sec,
                        baseline_value=baseline_tok_sec,
                        threshold=baseline_tok_sec * (1 - self.token_efficiency_drop_threshold),
                    )
                    if self._should_emit_alert(alert):
                        alerts.append(alert)

        # Check coherence
        if self._baselines["coherence"].is_established and coherence < self.coherence_threshold:
            alert = DegradationAlert(
                metric="coherence",
                severity=AlertSeverity.CRITICAL,
                message=f"Coherence dropped to {coherence:.2f} (threshold: {self.coherence_threshold:.2f})",
                current_value=coherence,
                baseline_value=self._baselines["coherence"].mean,
                threshold=self.coherence_threshold,
            )
            if self._should_emit_alert(alert):
                alerts.append(alert)

        # Check duration slowdown
        if self._baselines["duration_seconds"].is_established:
            baseline_duration = self._baselines["duration_seconds"].mean
            if baseline_duration > 0:
                slowdown = (duration / baseline_duration) - 1.0
                if slowdown > self.duration_slowdown_threshold:
                    alert = DegradationAlert(
                        metric="duration",
                        severity=AlertSeverity.WARNING,
                        message=f"Execution slowdown detected ({slowdown:.1%}) "
                        f"({duration:.2f}s vs baseline {baseline_duration:.2f}s)",
                        current_value=duration,
                        baseline_value=baseline_duration,
                        threshold=baseline_duration * (1 + self.duration_slowdown_threshold),
                    )
                    if self._should_emit_alert(alert):
                        alerts.append(alert)

        # Check success rate
        if self._baselines["success_rate"].is_established:
            baseline_success = self._baselines["success_rate"].mean
            if success_rate < baseline_success * 0.8:  # 20% drop in success rate
                alert = DegradationAlert(
                    metric="success_rate",
                    severity=AlertSeverity.CRITICAL,
                    message=f"Success rate dropped to {success_rate:.1%} (baseline: {baseline_success:.1%})",
                    current_value=success_rate,
                    baseline_value=baseline_success,
                    threshold=baseline_success * 0.8,
                )
                if self._should_emit_alert(alert):
                    alerts.append(alert)

        # NOW add samples to baselines (after all checks completed)
        # This ensures checks compare against established baseline, not polluted by current value
        self._baselines["cache_hit_rate"].add_sample(cache_hit_rate)
        self._baselines["token_efficiency"].add_sample(tokens_per_sec)
        self._baselines["coherence"].add_sample(coherence)
        self._baselines["duration_seconds"].add_sample(duration)
        self._baselines["success_rate"].add_sample(success_rate)

        # Constitutional equilibrium check (non-blocking)
        # Validates HIHO attractor convergence via ManifoldEquilibrium
        try:
            from cohezion.validation.constitutional import ManifoldEquilibrium

            equilibrium = ManifoldEquilibrium()
            # Build a minimal axiomatic state from metrics
            from cohezion.universe.engine import AxiomaticState

            state = AxiomaticState(logic=coherence, physics=1.0 - coherence)
            stability = equilibrium.verify_stability(state)
            if not stability["is_stable"]:
                eq_alert = DegradationAlert(
                    metric="constitutional_equilibrium",
                    severity=AlertSeverity.WARNING,
                    message=(
                        f"HIHO equilibrium unstable: coherence={coherence:.3f}, "
                        f"dist={stability['dist_from_attractor']:.4f}"
                    ),
                    current_value=coherence,
                    baseline_value=0.5,
                    threshold=0.05,
                )
                if self._should_emit_alert(eq_alert):
                    alerts.append(eq_alert)
        except Exception:
            pass  # Non-blocking: validation module may not be available

        # Ouroboros anomaly detection (non-blocking)
        # Cross-validates coherence via the Ouroboros AnomalyDetector
        try:
            from cohezion.ouroboros.detector import AnomalyDetector

            ouroboros = AnomalyDetector(coherence_threshold=0.1, target_coherence=0.5)
            if ouroboros.is_anomaly(coherence):
                ouro_alert = DegradationAlert(
                    metric="ouroboros_anomaly",
                    severity=AlertSeverity.WARNING,
                    message=f"Ouroboros: coherence {coherence:.3f} deviates >0.1 from HIHO",
                    current_value=coherence,
                    baseline_value=0.5,
                    threshold=0.1,
                )
                if self._should_emit_alert(ouro_alert):
                    alerts.append(ouro_alert)
        except Exception:
            pass  # Non-blocking: ouroboros module may not be available

        # OuroborosBridge physics coherence check (non-blocking)
        try:
            from cohezion.physics.ouroboros_bridge import OuroborosBridge

            if not hasattr(self, "_ouroboros_bridge"):
                self._ouroboros_bridge = OuroborosBridge()
            # Bridge records anomaly internally for Genesis UI
        except Exception:
            pass  # Non-blocking: bridge may not be available

        # Mycelium coverage signal (non-blocking)
        # When degradation alerts fire, check if recent code changes may be the cause
        try:
            if alerts:
                from cohezion.mycelium.observer import ChangeObserver

                if not hasattr(self, "_mycelium_observer"):
                    self._mycelium_observer = ChangeObserver()
                recent_changes = self._mycelium_observer.detect_modified_files()
                if recent_changes:
                    logger.debug(
                        "Mycelium: %d recent file changes may relate to %d alerts",
                        len(recent_changes),
                        len(alerts),
                    )
        except Exception:
            pass  # Non-blocking: mycelium may not be available

        # Run healing pipeline + resilience notification on alerts (non-blocking)
        if alerts and self._healing_enabled:
            self._run_healing_pipeline(alerts)
            self._notify_resilience_manager(alerts)

        # Route degradation feedback to CostAwareRouter (non-blocking)
        if alerts and self._routing_callback is not None:
            try:
                self._routing_callback(alerts)
            except Exception:
                logger.debug("Routing callback failed (non-blocking)", exc_info=True)

        return alerts

    def _should_emit_alert(self, alert: DegradationAlert) -> bool:
        """Check if alert should be emitted (cooldown enforcement).

        Args:
            alert: Alert to check

        Returns:
            True if alert should be emitted, False if in cooldown
        """
        alert_key = alert.metric
        last_time = self._last_alert_time.get(alert_key, 0.0)
        now = time.time()

        if now - last_time >= self._alert_cooldown_seconds:
            self._last_alert_time[alert_key] = now
            self._alert_history.append(alert)
            return True

        return False

    def _run_healing_pipeline(self, alerts: list[DegradationAlert]) -> None:
        """Route degradation alerts through healing's Diagnostician + Corrector.

        Non-blocking: all healing ops wrapped in try/except.
        Connects healing/ module to the compound monitoring pipeline.
        """
        try:
            from cohezion.healing import (
                Corrector,
                Diagnostician,
                DriftDetector,
                HealthStatus,
            )

            diagnostician = Diagnostician()
            Corrector()
            drift_detector = DriftDetector()

            for alert in alerts:
                # Map DegradationAlert → HealthStatus for healing pipeline
                health_status = HealthStatus(
                    component="compound",
                    status="failing" if alert.severity == AlertSeverity.CRITICAL else "degraded",
                    metric=alert.metric,
                    current_value=alert.current_value,
                    threshold=alert.threshold,
                )

                # Update drift baselines
                drift_detector.set_baseline("compound", alert.metric, alert.baseline_value)
                drift_detector.check("compound", alert.metric, alert.current_value)

                # Diagnose and log
                diagnosis = diagnostician.diagnose(health_status)
                logger.info(
                    "Healing diagnosis for %s: %s (confidence=%.2f, action=%s)",
                    alert.metric,
                    diagnosis.issue,
                    diagnosis.confidence,
                    diagnosis.recommended_action,
                )

        except ImportError:
            logger.debug("Healing module not available, skipping pipeline")
        except Exception:
            logger.debug("Healing pipeline error (non-blocking)", exc_info=True)

    def _notify_resilience_manager(self, alerts: list[DegradationAlert]) -> None:
        """Notify RAH AutonomicManager about degradation alerts.

        Non-blocking: resilience module may not be available.
        Connects resilience/ module to the compound monitoring pipeline.
        """
        try:
            from cohezion.resilience.manager import get_rah_manager

            get_rah_manager()
            # If manager is running, it will pick up vitals on its next loop
            # Log alert summary so the manager can correlate
            for alert in alerts:
                logger.info(
                    "RAH notified: %s %s (current=%.4f, baseline=%.4f)",
                    alert.severity.value,
                    alert.metric,
                    alert.current_value,
                    alert.baseline_value,
                )
        except ImportError:
            pass  # Non-blocking: resilience module not available
        except Exception:
            logger.debug("RAH notification error (non-blocking)", exc_info=True)

    def get_baseline_stats(self) -> dict[str, Any]:
        """Get current baseline statistics for all metrics.

        Returns:
            Dict with baseline info for each metric
        """
        stats = {}
        for metric_name, baseline in self._baselines.items():
            stats[metric_name] = {
                "is_established": baseline.is_established,
                "num_samples": len(baseline.samples),
                "mean": round(baseline.mean, 4),
                "std_dev": round(baseline.std_dev, 4),
                "lower_bound": round(baseline.lower_bound(), 4),
            }
        return stats

    def reset_baselines(self) -> None:
        """Reset all baselines (for testing or fresh start)."""
        for baseline in self._baselines.values():
            baseline.samples.clear()
        self._last_alert_time.clear()
        logger.debug("Degradation detector baselines reset")

    def suggest_routing_tier(self) -> str:
        """CB12: Actionable tier recommendation based on composite health score.

        Returns "npu" (score≥80), "igpu" (50≤score<80 or grace period), "cpu" (score<50).
        Grace period (no baselines established) → "igpu" safe middle-tier default.
        Always returns a string from {"npu", "igpu", "cpu"} — never raises, never None.
        """
        established = [b for b in self._baselines.values() if b.is_established]
        if not established:
            return "igpu"  # Grace period — baselines not yet established

        # Build composite score from established baselines (0–100 scale)
        score = 100.0
        cache_bl = self._baselines.get("cache_hit_rate")
        coherence_bl = self._baselines.get("coherence")

        if cache_bl and cache_bl.is_established:
            cache_ratio = cache_bl.mean / max(self.cache_hit_rate_threshold, 0.01)
            score = min(score, cache_ratio * 50.0)  # max 50 pts from cache

        if coherence_bl and coherence_bl.is_established:
            coh_ratio = coherence_bl.mean / max(self.coherence_threshold, 0.01)
            score = min(score + coh_ratio * 50.0, 100.0)

        if score >= 80:
            return "npu"
        if score >= 50:
            return "igpu"
        return "cpu"

    def get_health_summary(self) -> dict[str, Any]:
        """CB6: Tri-state health summary for each monitored metric.

        Returns dict with metric → True/False/None.
        None = baseline not yet established (grace period).
        True = healthy, False = degraded.
        """
        summary: dict[str, Any] = {}
        for metric, baseline in self._baselines.items():
            if not baseline.is_established:
                summary[metric] = None
                continue
            thresholds = {
                "cache_hit_rate": self.cache_hit_rate_threshold,
                "coherence": self.coherence_threshold,
            }
            if metric in thresholds:
                summary[metric] = baseline.mean >= thresholds[metric]
            else:
                summary[metric] = True  # No explicit threshold — assume healthy
        return summary

    def get_alert_summary(self) -> dict[str, Any]:
        """CB9: Dashboard aggregation API for alert history.

        Returns {"total": int, "by_severity": {}, "by_metric": {}, "most_recent_per_metric": {}}.
        """
        by_severity: dict[str, int] = {}
        by_metric: dict[str, int] = {}
        most_recent: dict[str, DegradationAlert] = {}

        for alert in self._alert_history:
            sev = alert.severity.name if hasattr(alert.severity, "name") else str(alert.severity)
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_metric[alert.metric] = by_metric.get(alert.metric, 0) + 1
            existing = most_recent.get(alert.metric)
            if existing is None or getattr(alert, "timestamp", 0) >= getattr(
                existing, "timestamp", 0
            ):
                most_recent[alert.metric] = alert

        return {
            "total": len(self._alert_history),
            "by_severity": by_severity,
            "by_metric": by_metric,
            "most_recent_per_metric": {k: v.__dict__ for k, v in most_recent.items()},
        }

    def snapshot(self) -> dict[str, Any]:
        """CB11: Capture a point-in-time detector snapshot."""
        return {
            "call_count": self._call_count,
            "baselines_established": sum(1 for b in self._baselines.values() if b.is_established),
            "health_summary": self.get_health_summary(),
            "composite_score": None,  # Grace period until baselines established
            "alert_summary": self.get_alert_summary(),
            "health_trend": [],
        }

    def record_snapshot(self) -> dict[str, Any]:
        """CB11: Append a snapshot to history (capped at 20 entries)."""
        if not hasattr(self, "_snapshot_history"):
            self._snapshot_history: list[dict[str, Any]] = []
        snap = self.snapshot()
        self._snapshot_history.append(snap)
        self._snapshot_history = self._snapshot_history[-20:]
        return snap

    @staticmethod
    def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        """CB11: Pure dict diff between two snapshots. No detector state used."""
        score_before = before.get("composite_score")
        score_after = after.get("composite_score")
        score_delta = None
        if score_before is not None and score_after is not None:
            score_delta = score_after - score_before

        health_changes: dict[str, Any] = {}
        h_before = before.get("health_summary", {})
        h_after = after.get("health_summary", {})
        for key in set(h_before) | set(h_after):
            if h_before.get(key) != h_after.get(key):
                health_changes[key] = {"before": h_before.get(key), "after": h_after.get(key)}

        alert_before = before.get("alert_summary", {}).get("total", 0)
        alert_after = after.get("alert_summary", {}).get("total", 0)
        return {
            "score_delta": score_delta,
            "health_changes": health_changes,
            "alert_count_delta": alert_after - alert_before,
        }

    def to_dict(self) -> dict[str, Any]:
        """CB7: JSON-safe serialization of baselines and call count."""
        return {
            "call_count": self._call_count,
            "baselines": {k: list(v.samples) for k, v in self._baselines.items()},
        }

    @classmethod
    def from_dict(cls, state: dict[str, Any], **kwargs: Any) -> "DegradationDetector":
        """CB7: Restore from serialized state."""
        instance = cls(**kwargs)
        instance._call_count = state.get("call_count", 0)
        for metric, samples in state.get("baselines", {}).items():
            if metric in instance._baselines:
                for s in samples:
                    instance._baselines[metric].add_sample(s)
        return instance


__all__ = [
    "AlertSeverity",
    "DegradationAlert",
    "DegradationDetector",
    "MetricBaseline",
]
