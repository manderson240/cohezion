# long lines: docstrings describing health contracts — wrapping reduces readability
"""Health observability layer for DegradationDetector (harness CB6-CB12).

Provides the read/aggregate side of degradation monitoring as a mixin so the
core ``degradation_detector.py`` stays under the 500-line hard limit. The host
class (``DegradationDetector``) owns the mutable state these methods read:

- ``_baselines``: dict[str, MetricBaseline] — moving averages per metric
- ``_call_count``: int — number of ``check_degradation`` invocations
- ``_alert_history``: list[DegradationAlert] — capped rolling buffer
- ``_snapshot_history``: list[dict] — capped health snapshots
- threshold attrs: cache_hit_rate_threshold, coherence_threshold,
  token_efficiency_drop_threshold

Tri-state convention (CB6/CB10): each metric is ``None`` while its baseline is
unestablished (grace period), then ``True`` (healthy) or ``False`` (degraded).
Health/degraded boundaries use the SAME threshold comparisons as
``check_degradation`` so the summary and the alerts can never disagree.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:  # pragma: no cover - type-only attribute contract from host class
    from cohezion.compound.degradation_detector import DegradationAlert, MetricBaseline


class HealthObservabilityMixin:
    """Read-only health/observability API mixed into DegradationDetector.

    All attributes are provided by the host ``DegradationDetector.__init__``;
    annotations below are type-only and never assigned here.
    """

    # Type-only attribute contract (assigned by the host class, not here).
    _baselines: dict[str, MetricBaseline]
    _call_count: int
    _alert_history: list[DegradationAlert]
    _snapshot_history: list[dict[str, Any]]
    _max_snapshot_history: int
    cache_hit_rate_threshold: float
    coherence_threshold: float
    token_efficiency_drop_threshold: float

    # ── Tri-state health (CB6, CB10) ─────────────────────────────────────────

    def get_health_summary(self) -> dict[str, bool | None]:
        """Tri-state health per monitored dimension.

        Returns ``{"cache": .., "token_efficiency": .., "coherence": ..}`` where
        each value is ``None`` (baseline not yet established), ``True`` (healthy)
        or ``False`` (degraded vs. the same threshold ``check_degradation`` uses.
        """
        cache = self._baselines["cache_hit_rate"]
        coh = self._baselines["coherence"]
        tok = self._baselines["token_efficiency"]

        cache_state: bool | None = (
            cache.mean >= self.cache_hit_rate_threshold if cache.is_established else None
        )
        coh_state: bool | None = (
            coh.mean >= self.coherence_threshold if coh.is_established else None
        )
        tok_state: bool | None = None
        if tok.is_established:
            latest = tok.samples[-1] if tok.samples else 0.0
            drop = 1.0 - (latest / tok.mean) if tok.mean > 0 else 0.0
            tok_state = drop <= self.token_efficiency_drop_threshold

        return {"cache": cache_state, "token_efficiency": tok_state, "coherence": coh_state}

    def get_composite_health_score(self) -> float | None:
        """Weighted 0-100 health score (coherence 40%, cache 30%, token 30%).

        ``None`` during the grace period (no dimension established). Renormalizes
        by the established-weight total so partial-None states score correctly.
        """
        summary = self.get_health_summary()
        weights = {"coherence": 0.40, "cache": 0.30, "token_efficiency": 0.30}
        total_weight = 0.0
        accumulated = 0.0
        for key, weight in weights.items():
            value = summary[key]
            if value is None:
                continue
            total_weight += weight
            accumulated += weight * (100.0 if value else 0.0)
        if total_weight == 0.0:
            return None
        return accumulated / total_weight

    def suggest_routing_tier(self) -> str:
        """Map composite health to a Triune routing tier.

        ``npu`` (score>=80), ``igpu`` (50<=score<80 or grace period), ``cpu``
        (score<50). Always a safe string in ``{"npu","igpu","cpu"}``.
        """
        score = self.get_composite_health_score()
        if score is None:
            return "igpu"
        if score >= 80.0:
            return "npu"
        if score >= 50.0:
            return "igpu"
        return "cpu"

    # ── Alert history (CB8, CB9) ─────────────────────────────────────────────

    def get_recent_alerts(self, n: int = 10) -> list[DegradationAlert]:
        """Return the last ``n`` emitted alerts (newest last). ``n<=0`` → []."""
        if n <= 0:
            return []
        return list(self._alert_history[-n:])

    def clear_alert_history(self) -> None:
        """Clear the rolling alert buffer (independent of baseline reset)."""
        self._alert_history.clear()

    def get_alert_summary(self) -> dict[str, Any]:
        """Aggregate alert counts for dashboards.

        Zero-state returns all-empty dicts. ``most_recent_per_metric`` keeps the
        latest alert object per metric (last write wins by timestamp).
        """
        by_severity: dict[str, int] = {}
        by_metric: dict[str, int] = {}
        most_recent: dict[str, DegradationAlert] = {}
        for alert in self._alert_history:
            sev = alert.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_metric[alert.metric] = by_metric.get(alert.metric, 0) + 1
            prev = most_recent.get(alert.metric)
            if prev is None or alert.timestamp >= prev.timestamp:
                most_recent[alert.metric] = alert
        return {
            "total": len(self._alert_history),
            "by_severity": by_severity,
            "by_metric": by_metric,
            "most_recent_per_metric": most_recent,
        }

    # ── Snapshots (CB11) ─────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        """Point-in-time health snapshot with exactly six contract keys."""
        return {
            "call_count": self._call_count,
            "baselines_established": {
                name: baseline.is_established for name, baseline in self._baselines.items()
            },
            "health_summary": self.get_health_summary(),
            "composite_score": self.get_composite_health_score(),
            "alert_summary": self.get_alert_summary(),
            "health_trend": self._compute_health_trend(),
        }

    def record_snapshot(self) -> dict[str, Any]:
        """Append a fresh snapshot to the capped history and return it."""
        snap = self.snapshot()
        self._snapshot_history.append(snap)
        if len(self._snapshot_history) > self._max_snapshot_history:
            self._snapshot_history = self._snapshot_history[-self._max_snapshot_history :]
        return snap

    @staticmethod
    def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        """Pure dict transform: deltas between two snapshots.

        ``score_delta`` is ``None`` if either composite score is ``None`` (grace
        period propagates). Identical snapshots → all-zero/empty deltas.
        """
        health_before = before.get("health_summary", {})
        health_after = after.get("health_summary", {})
        health_changes: dict[str, dict[str, Any]] = {}
        for key in set(health_before) | set(health_after):
            if health_before.get(key) != health_after.get(key):
                health_changes[key] = {
                    "before": health_before.get(key),
                    "after": health_after.get(key),
                }

        score_before = before.get("composite_score")
        score_after = after.get("composite_score")
        if score_before is None or score_after is None:
            score_delta: float | None = None
        else:
            score_delta = score_after - score_before

        alerts_before = before.get("alert_summary", {}).get("total", 0)
        alerts_after = after.get("alert_summary", {}).get("total", 0)
        return {
            "health_changes": health_changes,
            "score_delta": score_delta,
            "alert_count_delta": alerts_after - alerts_before,
        }

    def _compute_health_trend(self) -> str:
        """Trend of composite score vs. the most recent recorded snapshot."""
        if not self._snapshot_history:
            return "unknown"
        prev_score = self._snapshot_history[-1].get("composite_score")
        curr_score = self.get_composite_health_score()
        if prev_score is None or curr_score is None:
            return "unknown"
        if curr_score > prev_score:
            return "improving"
        if curr_score < prev_score:
            return "declining"
        return "stable"

    # ── Serialization (CB7) ──────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize call count + baseline samples for warm restart."""
        return {
            "call_count": self._call_count,
            "baselines": {
                name: list(baseline.samples) for name, baseline in self._baselines.items()
            },
        }

    @classmethod
    def from_dict(cls, state: dict[str, Any], **kwargs: Any) -> Any:
        """Reconstruct a detector, restoring baselines + call count.

        ``kwargs`` are forwarded to ``__init__`` for threshold overrides.
        """
        detector = cls(**kwargs)  # host class provides the concrete __init__
        detector._call_count = int(state.get("call_count", 0))
        for name, samples in state.get("baselines", {}).items():
            if name in detector._baselines:
                detector._baselines[name].samples = list(samples)
        return detector
