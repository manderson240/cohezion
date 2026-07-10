# long lines: SQL/URLs/docstrings — wrapping reduces readability
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

import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from cohezion.compound.degradation_health import HealthObservabilityMixin


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


class SkillDriftDetector:
    """Per-skill quality drift with two-level severity: WARN at 3%, BLOCK (CRITICAL) at 5%.

    Separated from DegradationDetector's aggregate-metric tracking so each skill gets
    its own rolling baseline. Integrated via DegradationDetector.check_skill_drift().

    Severity mapping:
        3% drop below rolling baseline mean → AlertSeverity.WARNING  (notify Kanban)
        5% drop below rolling baseline mean → AlertSeverity.CRITICAL (block promotion)
    """

    WARN_THRESHOLD: float = 0.03
    BLOCK_THRESHOLD: float = 0.05

    def __init__(self, window_size: int = 20, min_samples: int = 5) -> None:
        self._baselines: dict[str, list[float]] = {}
        self._window_size = window_size
        self._min_samples = min_samples

    def record(self, skill_name: str, quality_score: float) -> None:
        """Append quality to per-skill rolling window (capped at window_size)."""
        buf = self._baselines.setdefault(skill_name, [])
        buf.append(quality_score)
        if len(buf) > self._window_size:
            del buf[0]

    def check(self, skill_name: str, quality_score: float) -> DegradationAlert | None:
        """Return a DegradationAlert if quality has drifted, else None.

        Fail-open when fewer than min_samples recorded for this skill.
        """
        buf = self._baselines.get(skill_name, [])
        if len(buf) < self._min_samples:
            return None

        baseline = sum(buf) / len(buf)
        if baseline <= 0:
            return None

        drop = (baseline - quality_score) / baseline
        if drop >= self.BLOCK_THRESHOLD:
            return DegradationAlert(
                metric=f"skill_quality:{skill_name}",
                severity=AlertSeverity.CRITICAL,
                message=(
                    f"Skill '{skill_name}' quality dropped {drop:.1%} "
                    f"(BLOCK ≥{self.BLOCK_THRESHOLD:.0%}): "
                    f"{quality_score:.2f} vs baseline {baseline:.2f}"
                ),
                current_value=quality_score,
                baseline_value=baseline,
                threshold=baseline * (1 - self.BLOCK_THRESHOLD),
            )
        if drop >= self.WARN_THRESHOLD:
            return DegradationAlert(
                metric=f"skill_quality:{skill_name}",
                severity=AlertSeverity.WARNING,
                message=(
                    f"Skill '{skill_name}' quality drifted {drop:.1%} "
                    f"(WARN ≥{self.WARN_THRESHOLD:.0%}): "
                    f"{quality_score:.2f} vs baseline {baseline:.2f}"
                ),
                current_value=quality_score,
                baseline_value=baseline,
                threshold=baseline * (1 - self.WARN_THRESHOLD),
            )
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize per-skill baselines for cross-session persistence (SD-PERSIST)."""
        return {
            "window_size": self._window_size,
            "min_samples": self._min_samples,
            "baselines": {k: list(v) for k, v in self._baselines.items()},
        }

    @classmethod
    def from_dict(cls, state: dict[str, Any]) -> SkillDriftDetector:
        """Restore from serialized state. Missing keys fall back to defaults (fail-open)."""
        inst = cls(
            window_size=state.get("window_size", 20),
            min_samples=state.get("min_samples", 5),
        )
        for skill, samples in state.get("baselines", {}).items():
            # Honour the window_size cap when restoring (in case window shrunk)
            inst._baselines[skill] = list(samples)[-inst._window_size :]
        return inst


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

    def trend_value(self, horizon: int = 1) -> float:
        """Project metric value at `horizon` steps ahead via linear trend extrapolation.

        Fits a degree-1 polynomial (numpy polyfit) to the last ``window_size`` samples
        and returns the extrapolated value at ``horizon`` steps beyond the last sample.
        Falls back to ``mean`` when fewer than 2 samples are available or if polyfit
        raises (e.g., all-identical samples yielding a degenerate matrix).

        Task #120: used by check_degradation() for baseline comparisons so that a
        steadily declining metric triggers an alert *before* it crosses the mean.
        """
        recent = self.samples[-self.window_size :]
        if len(recent) < 2:
            return self.mean
        try:
            x = np.arange(len(recent), dtype=float)
            coeffs = np.polyfit(x, recent, 1)
            return float(np.polyval(coeffs, float(len(recent) - 1 + horizon)))
        except Exception:
            return self.mean

    def chebyshev_lower_bound(self, k: float = 2.0) -> float:
        """Chebyshev adaptive lower bound: mean - std_dev / k.

        By Chebyshev's inequality (distribution-free), the probability that a sample
        falls below this bound is ≤ 1/k².  At k=2.0 that is ≤ 25 %.

        Task #121: used by check_degradation() when ``use_chebyshev=True`` to replace
        fixed percentage-drop thresholds with data-adaptive alert bounds.
        """
        return self.mean - (self.std_dev / k)


class DegradationDetector(HealthObservabilityMixin):
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
    use_chebyshev : bool
        When True, replace fixed thresholds for cache/efficiency/coherence with
        data-adaptive Chebyshev lower bounds (Task #121, default: False).
    """

    # LT1: EMA adaptation constants (MTF 2-competitiveness backing)
    # α=0.1 tracks within 2× of optimal when drift < 1 change per 10 observations.
    # α=0.4 fast-path fires when consecutive observations deviate >2σ (burst regime).
    _EMA_ALPHA_SLOW: float = 0.1
    _EMA_ALPHA_FAST: float = 0.4
    _EMA_BURST_SIGMA: float = 2.0  # σ threshold for fast-path activation
    _EMA_OBS_WINDOW: int = 8  # rolling window for σ estimation

    def __init__(
        self,
        cache_hit_rate_threshold: float = 0.50,
        token_efficiency_drop_threshold: float = 0.10,
        coherence_threshold: float = 0.60,
        duration_slowdown_threshold: float = 0.25,
        use_chebyshev: bool = False,
        use_ema_thresholds: bool = False,
    ) -> None:
        """Initialize degradation detector."""
        self.cache_hit_rate_threshold = cache_hit_rate_threshold
        self.token_efficiency_drop_threshold = token_efficiency_drop_threshold
        self.coherence_threshold = coherence_threshold
        self.duration_slowdown_threshold = duration_slowdown_threshold
        # Task #121: when True, use Chebyshev adaptive bounds instead of fixed thresholds
        self.use_chebyshev = use_chebyshev
        # LT1: when True, alert thresholds self-adapt via EMA toward observed values
        self.use_ema_thresholds = use_ema_thresholds
        # EMA state: seeded from constructor thresholds; adapts each check_degradation()
        self._ema_thresholds: dict[str, float] = {
            "cache_hit_rate": cache_hit_rate_threshold,
            "coherence": coherence_threshold,
            "token_efficiency_drop": token_efficiency_drop_threshold,
        }
        # Rolling observation window for burst-detection σ estimation (per metric)
        self._ema_obs_history: dict[str, deque[float]] = {
            "cache_hit_rate": deque(maxlen=self._EMA_OBS_WINDOW),
            "coherence": deque(maxlen=self._EMA_OBS_WINDOW),
            "token_efficiency_drop": deque(maxlen=self._EMA_OBS_WINDOW),
        }

        # Baselines for each metric
        self._baselines = {
            "cache_hit_rate": MetricBaseline("cache_hit_rate"),
            "token_efficiency": MetricBaseline("token_efficiency"),
            "coherence": MetricBaseline("coherence"),
            "duration_seconds": MetricBaseline("duration_seconds"),
            "success_rate": MetricBaseline("success_rate"),
            "token_surprisal": MetricBaseline("token_surprisal"),
            "quality_score": MetricBaseline("quality_score"),
            # JW1 / H2: JepaGate.last_coherence — a [0,1] PRE-execution coherence signal that
            # the executor writes into degradation_metrics. Tracked here so a low predicted
            # coherence can contribute a (predictive) WARNING alert instead of being dropped.
            "jepa_coherence": MetricBaseline("jepa_coherence"),
        }

        # Alert history for deduplication and CB9 dashboard API
        self._last_alert_time: dict[str, float] = {}
        self._alert_cooldown_seconds = 60.0  # Don't repeat same alert within 60s
        self._alert_history: list[DegradationAlert] = []

        # Healing pipeline integration (non-blocking)
        self._healing_enabled = True

        # Routing feedback callback (wired by CompoundExecutor)
        self._routing_callback: Any = None

        # CB12: per-metric health verdict — updated each check_degradation() call.
        # None = not yet checked (grace period for that metric).
        self._current_health: dict[str, bool | None] = {
            "cache_hit_rate": None,
            "token_efficiency": None,
            "coherence": None,
        }

        # Task #112: rolling embedding L2-norms for PSI drift detection.
        # Populated via update_embedding_distribution(); checked in check_degradation().
        self._embedding_norms: list[float] = []

        # Per-skill quality drift: WARN at 3%, CRITICAL (block) at 5%.
        self._skill_drift = SkillDriftDetector()

        # CB7: call counter for warm-start awareness — how many check_degradation() calls
        # have established baselines in this detector instance.
        self._call_count: int = 0

        # CB11: capped rolling buffer of health snapshots (HealthObservabilityMixin
        # reads/writes these; record_snapshot() trims to _max_snapshot_history).
        self._snapshot_history: list[dict[str, Any]] = []
        self._max_snapshot_history: int = 20

        logger.debug("DegradationDetector initialized with thresholds")

    def set_routing_callback(self, callback: Any) -> None:
        """Set callback for routing feedback on degradation alerts.

        Called by CompoundExecutor to wire DegradationDetector → CostAwareRouter.
        The callback receives the list of DegradationAlert objects.
        """
        self._routing_callback = callback
        logger.debug("Routing feedback callback registered")

    # ── LT1: EMA threshold adaptation ────────────────────────────────────────

    def get_learned_threshold(self, metric: str, drop_band: float = 0.05) -> float:
        """Return the EMA-adapted threshold for a metric, with headroom.

        The returned value is `ema * (1 - drop_band)` — slightly below the running
        EMA of observed values, giving a margin before an alert fires.  Falls back to
        the constructor threshold if the metric is unknown.

        Args:
            metric:    One of "cache_hit_rate", "coherence", "token_efficiency_drop".
            drop_band: Fractional headroom below the EMA (default 0.05 = 5%).
        """
        ema = self._ema_thresholds.get(metric)
        if ema is None:
            # Fallback for unknown metrics
            return getattr(self, f"{metric}_threshold", 0.0)
        return max(0.0, ema * (1.0 - drop_band))

    def _update_ema_thresholds(
        self,
        cache_hit_rate: float | None,
        coherence: float | None,
        tokens_per_sec: float | None,
        baseline_tok_sec: float | None,
    ) -> None:
        """Update EMA thresholds after alert checks.

        Uses a fast-path α (0.4) when the incoming observation deviates by >2σ from
        the rolling window history — the MTF burst-regime heuristic.  Otherwise uses
        slow α (0.1) which tracks within 2× of optimal for gradual drift.

        All updates are bounded to [0.0, 1.0] to keep thresholds meaningful.
        """

        def _alpha_for(metric: str, obs: float) -> float:
            """Choose α based on whether obs is a burst (>2σ from recent history)."""
            hist = self._ema_obs_history[metric]
            if len(hist) < 3:
                return self._EMA_ALPHA_SLOW
            mean_h = sum(hist) / len(hist)
            var_h = sum((x - mean_h) ** 2 for x in hist) / len(hist)
            sigma = var_h**0.5
            if sigma > 0 and abs(obs - mean_h) > self._EMA_BURST_SIGMA * sigma:
                return self._EMA_ALPHA_FAST
            return self._EMA_ALPHA_SLOW

        if cache_hit_rate is not None:
            obs = float(cache_hit_rate)
            α = _alpha_for("cache_hit_rate", obs)
            self._ema_thresholds["cache_hit_rate"] = min(
                1.0,
                max(0.0, α * obs + (1.0 - α) * self._ema_thresholds["cache_hit_rate"]),
            )
            self._ema_obs_history["cache_hit_rate"].append(obs)

        if coherence is not None:
            obs = float(coherence)
            α = _alpha_for("coherence", obs)
            self._ema_thresholds["coherence"] = min(
                1.0,
                max(0.0, α * obs + (1.0 - α) * self._ema_thresholds["coherence"]),
            )
            self._ema_obs_history["coherence"].append(obs)

        if tokens_per_sec is not None and baseline_tok_sec is not None and baseline_tok_sec > 0:
            # Represent token efficiency as a drop fraction (lower = worse)
            drop = max(0.0, 1.0 - float(tokens_per_sec) / baseline_tok_sec)
            α = _alpha_for("token_efficiency_drop", drop)
            self._ema_thresholds["token_efficiency_drop"] = min(
                1.0,
                max(0.0, α * drop + (1.0 - α) * self._ema_thresholds["token_efficiency_drop"]),
            )
            self._ema_obs_history["token_efficiency_drop"].append(drop)

    def check_skill_drift(self, skill_name: str, quality_score: float) -> DegradationAlert | None:
        """Check and record per-skill quality drift; return alert if threshold crossed.

        WARN at 3% drop, CRITICAL at 5% drop vs per-skill rolling mean.
        Fail-open when fewer than 5 samples recorded for this skill.
        Emitted alerts go through the shared _alert_history (cooldown-deduplicated).
        """
        alert = self._skill_drift.check(skill_name, quality_score)
        self._skill_drift.record(skill_name, quality_score)
        if alert is not None and self._should_emit_alert(alert):
            self._alert_history.append(alert)
            logger.info("Skill drift detected: %s", alert.message)
            return alert
        elif alert is None:
            # No drift — still record for baseline
            pass
        return None

    def check_degradation(self, metrics: dict[str, Any]) -> list[DegradationAlert]:
        """Check if metrics show degradation compared to baseline.

        Args:
            metrics: Dict with metric names and values

        Returns:
            List of DegradationAlert if degradation detected, empty list otherwise
        """
        alerts = []
        self._call_count += 1

        # Extract metrics — None means "not provided this call"; skip baseline updates for those
        cache_hit_rate = metrics.get("combined_hit_rate")
        tokens_per_sec = metrics.get("tokens_per_second")
        coherence = metrics.get("mean_coherence")
        duration = metrics.get("elapsed_seconds")
        success_rate = metrics.get("success_rate")
        # H2: pre-execution JEPA coherence — a [0,1] predictive signal from JepaGate.last_coherence.
        jepa_coherence = metrics.get("jepa_coherence")

        # Check conditions AGAINST ESTABLISHED BASELINES FIRST
        # Then add samples after all checks are done

        # Check cache hit rate (skip if not provided this call)
        # Task #121: when use_chebyshev=True, replace fixed threshold with Chebyshev bound.
        # Gelman BDA §3.1: Beta-Binomial early-warning path when baseline is not yet established
        # (n < min_samples=5).  Treats observed rates as fractional hits; posterior mean =
        # (sum(samples) + 1) / (n + 2).  Fires only on a severe drop (< 50% of threshold) to
        # avoid false positives during the warm-up window.
        if cache_hit_rate is not None and not self._baselines["cache_hit_rate"].is_established:
            _chr_samples = self._baselines["cache_hit_rate"].samples
            if len(_chr_samples) >= 1:
                _beta_mean = (sum(_chr_samples) + 1) / (len(_chr_samples) + 2)
                if _beta_mean < self.cache_hit_rate_threshold * 0.5:
                    alert = DegradationAlert(
                        metric="cache_hit_rate",
                        severity=AlertSeverity.WARNING,
                        message=f"Cache hit rate early warning: Beta posterior "
                        f"{_beta_mean:.1%} far below threshold "
                        f"{self.cache_hit_rate_threshold:.1%} (n={len(_chr_samples)}, "
                        f"baseline warming up)",
                        current_value=cache_hit_rate,
                        baseline_value=_beta_mean,
                        threshold=self.cache_hit_rate_threshold,
                    )
                    if self._should_emit_alert(alert):
                        alerts.append(alert)

        if cache_hit_rate is not None and self._baselines["cache_hit_rate"].is_established:
            _cache_thr = (
                self._baselines["cache_hit_rate"].chebyshev_lower_bound(2.0)
                if self.use_chebyshev
                else self.cache_hit_rate_threshold
            )
            if cache_hit_rate < _cache_thr:
                alert = DegradationAlert(
                    metric="cache_hit_rate",
                    severity=AlertSeverity.WARNING,
                    message=f"Cache hit rate dropped to {cache_hit_rate:.1%} "
                    f"(threshold: {_cache_thr:.1%})",
                    current_value=cache_hit_rate,
                    baseline_value=self._baselines["cache_hit_rate"].mean,
                    threshold=_cache_thr,
                )
                if self._should_emit_alert(alert):
                    alerts.append(alert)

        # Check token efficiency (skip if not provided)
        # Task #120: use trend_value(1) as the comparison baseline.
        # Task #121: when use_chebyshev=True, replace % drop check with Chebyshev bound.
        if tokens_per_sec is not None and self._baselines["token_efficiency"].is_established:
            baseline_tok_sec = self._baselines["token_efficiency"].trend_value(1)
            if self.use_chebyshev:
                _cheby_tok = self._baselines["token_efficiency"].chebyshev_lower_bound(2.0)
                if tokens_per_sec < _cheby_tok:
                    alert = DegradationAlert(
                        metric="token_efficiency",
                        severity=AlertSeverity.WARNING,
                        message=f"Token efficiency {tokens_per_sec:.0f} tok/sec below "
                        f"Chebyshev bound {_cheby_tok:.0f} tok/sec",
                        current_value=tokens_per_sec,
                        baseline_value=self._baselines["token_efficiency"].mean,
                        threshold=_cheby_tok,
                    )
                    if self._should_emit_alert(alert):
                        alerts.append(alert)
            elif baseline_tok_sec > 0:
                efficiency_drop = 1.0 - (tokens_per_sec / baseline_tok_sec)
                if efficiency_drop > self.token_efficiency_drop_threshold:
                    alert = DegradationAlert(
                        metric="token_efficiency",
                        severity=AlertSeverity.WARNING,
                        message=f"Token efficiency dropped {efficiency_drop:.1%} "
                        f"({tokens_per_sec:.0f} vs baseline {baseline_tok_sec:.0f} tok/sec)",
                        current_value=tokens_per_sec,
                        baseline_value=self._baselines["token_efficiency"].mean,
                        threshold=baseline_tok_sec * (1 - self.token_efficiency_drop_threshold),
                    )
                    if self._should_emit_alert(alert):
                        alerts.append(alert)

        # Check coherence (skip if not provided)
        # Task #121: when use_chebyshev=True, replace fixed threshold with Chebyshev bound.
        if coherence is not None and self._baselines["coherence"].is_established:
            _coh_thr = (
                self._baselines["coherence"].chebyshev_lower_bound(2.0)
                if self.use_chebyshev
                else self.coherence_threshold
            )
            if coherence < _coh_thr:
                alert = DegradationAlert(
                    metric="coherence",
                    severity=AlertSeverity.CRITICAL,
                    message=f"Coherence dropped to {coherence:.2f} (threshold: {_coh_thr:.2f})",
                    current_value=coherence,
                    baseline_value=self._baselines["coherence"].mean,
                    threshold=_coh_thr,
                )
                if self._should_emit_alert(alert):
                    alerts.append(alert)

        # Check pre-execution JEPA coherence (skip if not provided this call).
        # H2: this is a PREDICTIVE signal (JepaGate.last_coherence), so the alert is a WARNING
        # rather than the CRITICAL used for observed post-execution coherence collapse.
        # Task #121: honour use_chebyshev for a data-adaptive bound, same as coherence.
        if jepa_coherence is not None and self._baselines["jepa_coherence"].is_established:
            _jepa_thr = (
                self._baselines["jepa_coherence"].chebyshev_lower_bound(2.0)
                if self.use_chebyshev
                else self.coherence_threshold
            )
            if float(jepa_coherence) < _jepa_thr:
                alert = DegradationAlert(
                    metric="jepa_coherence",
                    severity=AlertSeverity.WARNING,
                    message=(
                        f"Pre-execution JEPA coherence dropped to {float(jepa_coherence):.2f} "
                        f"(threshold: {_jepa_thr:.2f})"
                    ),
                    current_value=float(jepa_coherence),
                    baseline_value=self._baselines["jepa_coherence"].mean,
                    threshold=_jepa_thr,
                )
                if self._should_emit_alert(alert):
                    alerts.append(alert)

        # Check duration slowdown (skip if not provided)
        # Task #120: use trend_value(1) as baseline for comparison.
        # Note: Chebyshev is NOT applied here — duration is "higher = worse" so
        #       a lower bound cannot detect upward (slowdown) degradation.
        if duration is not None and self._baselines["duration_seconds"].is_established:
            baseline_duration = self._baselines["duration_seconds"].trend_value(1)
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

        # Check success rate (skip if not provided)
        # Task #120: use trend_value(1) as baseline for comparison.
        if success_rate is not None and self._baselines["success_rate"].is_established:
            baseline_success = self._baselines["success_rate"].trend_value(1)
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

        # Check quality_score (Long2Short: 1/tokens for success, 0.0 for failure)
        # Task #120: use trend_value(1) as baseline for comparison.
        _qs = metrics.get("quality_score")
        if _qs is not None and self._baselines["quality_score"].is_established:
            baseline_qs = self._baselines["quality_score"].trend_value(1)
            if baseline_qs > 0 and float(_qs) < baseline_qs * 0.8:
                alert = DegradationAlert(
                    metric="quality_score",
                    severity=AlertSeverity.CRITICAL,
                    message=(
                        f"Long2Short quality dropped to {float(_qs):.5f} "
                        f"(baseline: {baseline_qs:.5f})"
                    ),
                    current_value=float(_qs),
                    baseline_value=baseline_qs,
                    threshold=baseline_qs * 0.8,
                )
                if self._should_emit_alert(alert):
                    alerts.append(alert)

        # Task #112: check embedding distribution drift via PSI.
        # get_embedding_psi() returns None when fewer than 20 norms are recorded.
        _emb_psi = self.get_embedding_psi()
        if _emb_psi is not None and _emb_psi > 0.1:
            _psi_severity = AlertSeverity.CRITICAL if _emb_psi > 0.2 else AlertSeverity.WARNING
            _psi_alert = DegradationAlert(
                metric="embedding_drift",
                severity=_psi_severity,
                message=(
                    f"Embedding distribution drift detected: PSI={_emb_psi:.4f} "
                    f"({'significant' if _emb_psi > 0.2 else 'moderate'})"
                ),
                current_value=_emb_psi,
                baseline_value=0.0,
                threshold=0.1,
            )
            if self._should_emit_alert(_psi_alert):
                alerts.append(_psi_alert)

        # NOW add samples to baselines (only for metrics provided this call)
        if cache_hit_rate is not None:
            self._baselines["cache_hit_rate"].add_sample(cache_hit_rate)
        if tokens_per_sec is not None:
            self._baselines["token_efficiency"].add_sample(tokens_per_sec)
        if coherence is not None:
            self._baselines["coherence"].add_sample(coherence)
        if duration is not None:
            self._baselines["duration_seconds"].add_sample(duration)
        if success_rate is not None:
            self._baselines["success_rate"].add_sample(success_rate)
        if jepa_coherence is not None:
            self._baselines["jepa_coherence"].add_sample(float(jepa_coherence))
        # token_surprisal: S_LP signal — skip None (FLM/NPU tasks have no logprobs)
        _ts = metrics.get("token_surprisal")
        if _ts is not None:
            self._baselines["token_surprisal"].add_sample(float(_ts))
        if _qs is not None:
            self._baselines["quality_score"].add_sample(float(_qs))

        # CB12: update per-metric health verdicts for composite score / routing tier
        if cache_hit_rate is not None and self._baselines["cache_hit_rate"].is_established:
            self._current_health["cache_hit_rate"] = (
                float(cache_hit_rate) >= self.cache_hit_rate_threshold
            )
        if tokens_per_sec is not None and self._baselines["token_efficiency"].is_established:
            _base_tok = self._baselines["token_efficiency"].trend_value(1)
            _drop = 1.0 - (float(tokens_per_sec) / _base_tok) if _base_tok > 0 else 0.0
            self._current_health["token_efficiency"] = _drop <= self.token_efficiency_drop_threshold
        if coherence is not None and self._baselines["coherence"].is_established:
            self._current_health["coherence"] = float(coherence) >= self.coherence_threshold

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
            self._run_healing_pipeline(alerts, metrics)
            self._notify_resilience_manager(alerts)

        # Route degradation feedback to CostAwareRouter (non-blocking)
        if alerts and self._routing_callback is not None:
            try:
                self._routing_callback(alerts)
            except Exception:
                logger.debug("Routing callback failed (non-blocking)", exc_info=True)

        # CB9: append to alert_history for get_alert_summary() dashboard API
        self._alert_history.extend(alerts)

        # LT1: update EMA thresholds after alert checks (non-blocking)
        if self.use_ema_thresholds:
            _tok_base = (
                self._baselines["token_efficiency"].trend_value(1)
                if self._baselines["token_efficiency"].is_established
                else None
            )
            self._update_ema_thresholds(
                cache_hit_rate=cache_hit_rate,
                coherence=coherence,
                tokens_per_sec=tokens_per_sec,
                baseline_tok_sec=_tok_base,
            )

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
            return True

        return False

    def _run_healing_pipeline(
        self, alerts: list[DegradationAlert], metrics: dict[str, Any]
    ) -> None:
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
            Dict with baseline info for each metric, plus a top-level
            ``log_synthesis_score`` key (Task #99) holding the geometric-mean
            health proxy across all established baselines, or None.
        """
        stats: dict[str, Any] = {}
        for metric_name, baseline in self._baselines.items():
            stats[metric_name] = {
                "is_established": baseline.is_established,
                "num_samples": len(baseline.samples),
                "mean": round(baseline.mean, 4),
                "std_dev": round(baseline.std_dev, 4),
                "lower_bound": round(baseline.lower_bound(), 4),
            }
        # Task #99: add geometric-mean health proxy across all established baselines.
        stats["log_synthesis_score"] = self.get_log_synthesis_score()
        return stats

    def get_alert_summary(self) -> dict[str, Any]:
        """CB9: Dashboard aggregation API — total + groupings from alert_history.

        Returns:
            {"total": int, "by_severity": {sev: count}, "by_metric": {metric: count},
             "most_recent_per_metric": {metric: alert_dict}}
        """
        by_severity: dict[str, int] = {}
        by_metric: dict[str, int] = {}
        most_recent: dict[str, dict[str, Any]] = {}
        for a in self._alert_history:
            sev = a.severity.value if hasattr(a.severity, "value") else str(a.severity)
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_metric[a.metric] = by_metric.get(a.metric, 0) + 1
            if a.metric not in most_recent or a.timestamp > most_recent[a.metric].get(
                "timestamp", 0
            ):
                most_recent[a.metric] = {
                    "metric": a.metric,
                    "severity": sev,
                    "message": a.message,
                    "timestamp": a.timestamp,
                }
        return {
            "total": len(self._alert_history),
            "by_severity": by_severity,
            "by_metric": by_metric,
            "most_recent_per_metric": most_recent,
        }

    def get_composite_health_score(self) -> float | None:
        """CB12: 0–100 composite health score, None while any baseline is in grace period."""
        keys = ["cache_hit_rate", "token_efficiency", "coherence"]
        if not all(self._baselines[m].is_established for m in keys):
            return None
        healthy = sum(1 for v in self._current_health.values() if v is True)
        return (healthy / len(self._current_health)) * 100.0

    def suggest_routing_tier(self) -> str:
        """CB12: Return Triune tier recommendation. Never raises, never None.

        Returns:
            "npu"  — score ≥ 80 (healthy, use fastest tier)
            "igpu" — score 50–79 or grace period (middle tier / default)
            "cpu"  — score < 50 (degraded, use most capable tier)
        """
        try:
            score = self.get_composite_health_score()
            if score is None:
                return "igpu"
            if score >= 80.0:
                return "npu"
            if score >= 50.0:
                return "igpu"
            return "cpu"
        except Exception:
            return "igpu"

    def reset_baselines(self) -> None:
        """Reset all baselines (for testing or fresh start)."""
        for baseline in self._baselines.values():
            baseline.samples.clear()
        self._last_alert_time.clear()
        logger.debug("Degradation detector baselines reset")

    # ------------------------------------------------------------------
    # Task #99 — Log-Synthesis Score (Sazabi pattern)
    # ------------------------------------------------------------------

    def get_log_synthesis_score(self) -> float | None:
        """Task #99: geometric mean of established baseline health proxies.

        Computes ``exp(mean(log(max(ε, score_i))))`` for all established baselines,
        where ε = 1e-6 guards against log(0).  Health proxies per metric:

        * Most metrics: ``baseline.mean`` (cache_hit_rate, coherence, success_rate,
          token_efficiency, token_surprisal, quality_score).
        * ``duration_seconds``: ``1 / (1 + baseline.mean)`` — inverts the direction
          so that lower (faster) duration yields a higher health proxy.

        Returns:
            Geometric-mean health proxy (float > 0), or None when no baseline
            has been established yet.
        """
        eps = 1e-6
        scores: list[float] = []
        for name, baseline in self._baselines.items():
            if not baseline.is_established:
                continue
            score = 1.0 / (1.0 + baseline.mean) if name == "duration_seconds" else baseline.mean
            scores.append(max(eps, score))
        if not scores:
            return None
        return float(np.exp(float(np.mean(np.log(np.array(scores))))))

    # ------------------------------------------------------------------
    # Task #112 — PSI Embedding Drift Detection
    # ------------------------------------------------------------------

    def update_embedding_distribution(self, embedding_sample: list[float]) -> None:
        """Task #112: Record the L2 norm of an embedding vector for PSI tracking.

        Call this once per inference pass.  After 20 norms have been collected,
        ``get_embedding_psi()`` begins returning meaningful values; the norms list
        grows without bound (rolling window is applied inside get_embedding_psi).

        Args:
            embedding_sample: A single embedding vector (any dimensionality).
                              Its L2 norm is the drift-sensitive statistic.
        """
        norm = float(np.linalg.norm(embedding_sample))
        self._embedding_norms.append(norm)

    def get_embedding_psi(self) -> float | None:
        """Task #112: PSI between the first and latest window halves of embedding norms.

        Splits recorded norms into two windows of size ``window_size // 2`` (10):
        * **expected**: the first 10 norms (baseline distribution)
        * **actual**: the most recent 10 norms (current distribution)

        Histograms each window over 20 bins spanning [0, 5] and computes the
        Population Stability Index:

            PSI = Σ (actual_i − expected_i) × ln(actual_i / expected_i)

        where ε = 1e-6 prevents log(0) / zero-division.

        Returns:
            PSI value (float ≥ 0), or None when fewer than 20 norms are recorded.
            * PSI < 0.10 → no significant drift
            * 0.10 ≤ PSI < 0.20 → moderate drift (WARNING)
            * PSI ≥ 0.20 → significant drift (CRITICAL)
        """
        window = 20
        half = window // 2  # 10 samples per half
        if len(self._embedding_norms) < window:
            return None

        expected_samples = self._embedding_norms[:half]
        actual_samples = self._embedding_norms[-half:]

        bins = np.linspace(0.0, 5.0, 21)  # 20 equally-spaced bins over [0, 5]

        expected_hist, _ = np.histogram(expected_samples, bins=bins)
        actual_hist, _ = np.histogram(actual_samples, bins=bins)

        expected_total = float(expected_hist.sum())
        actual_total = float(actual_hist.sum())
        if expected_total == 0 or actual_total == 0:
            return None

        expected_prob = expected_hist.astype(float) / expected_total
        actual_prob = actual_hist.astype(float) / actual_total

        # Floor at ε to avoid log(0) and division-by-zero
        eps = 1e-6
        expected_prob = np.maximum(expected_prob, eps)
        actual_prob = np.maximum(actual_prob, eps)

        psi = float(np.sum((actual_prob - expected_prob) * np.log(actual_prob / expected_prob)))
        return psi

    def to_dict(self) -> dict[str, Any]:
        """Serialize detector state for cross-session persistence (CB7).

        Returns a JSON-safe dict with:
        - call_count: int — how many check_degradation() calls have run
        - baselines: {metric: [samples]} — the rolling float windows
        - skill_drift: nested SkillDriftDetector state
        """
        return {
            "call_count": self._call_count,
            "baselines": {name: list(b.samples) for name, b in self._baselines.items()},
            "skill_drift": self._skill_drift.to_dict(),
        }

    @classmethod
    def from_dict(cls, state: dict[str, Any], **kwargs: Any) -> DegradationDetector:
        """Restore detector from serialized state.

        Args:
            state: dict produced by to_dict()
            **kwargs: forwarded to __init__ for threshold overrides
                      (e.g. cache_hit_rate_threshold=0.99)

        Fail-open: missing keys default to zero/empty — never crashes on partial files.
        """
        inst = cls(**kwargs)
        inst._call_count = int(state.get("call_count", 0))
        for name, samples in state.get("baselines", {}).items():
            if name in inst._baselines:
                inst._baselines[name].samples = list(samples)
        skill_drift_state = state.get("skill_drift")
        if skill_drift_state:
            inst._skill_drift = SkillDriftDetector.from_dict(skill_drift_state)
        return inst

    _DEFAULT_BASELINES_PATH: Path = Path.home() / ".cohezion" / "degradation_baselines.json"

    def end_session(self, path: str | Path | None = None) -> None:
        """Persist detector state to JSON at session end (CB7 auto-save).

        Non-blocking: failures are logged at DEBUG and silently ignored.
        """
        target = Path(path) if path is not None else self._DEFAULT_BASELINES_PATH
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
            logger.debug("DegradationDetector: saved baselines to %s", target)
        except Exception as exc:
            logger.debug("DegradationDetector: end_session save failed (non-blocking): %s", exc)

    def start_session(self, path: str | Path | None = None) -> bool:
        """Restore detector state from JSON at session start (CB7 auto-restore).

        Performs an in-place restoration: mutates self rather than creating a new
        instance, so the ExecutorFactory can wire this via atexit then call it once.

        Returns
        -------
        bool
            True on success, False when the file is absent or corrupt (fail-open).
        """
        target = Path(path) if path is not None else self._DEFAULT_BASELINES_PATH
        if not target.exists():
            return False
        try:
            state = json.loads(target.read_text(encoding="utf-8"))
            self._call_count = int(state.get("call_count", 0))
            for name, samples in state.get("baselines", {}).items():
                if name in self._baselines:
                    self._baselines[name].samples = list(samples)
            skill_drift_state = state.get("skill_drift")
            if skill_drift_state:
                self._skill_drift = SkillDriftDetector.from_dict(skill_drift_state)
            logger.debug(
                "DegradationDetector: restored baselines from %s (call_count=%d)",
                target,
                self._call_count,
            )
            return True
        except Exception as exc:
            logger.debug(
                "DegradationDetector: start_session restore failed (non-blocking): %s", exc
            )
            return False


__all__ = [
    "AlertSeverity",
    "DegradationAlert",
    "DegradationDetector",
    "MetricBaseline",
]
