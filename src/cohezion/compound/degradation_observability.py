"""Observability extension for DegradationDetector.

Extracted from degradation_detector.py to keep that file under the 500-line
hard limit. Adds health summaries, serialization, snapshot diffing, and the
routing-tier recommendation that close the monitoring → routing feedback loop.

All methods are non-blocking; errors return safe zero-state defaults.
"""

from __future__ import annotations

import contextlib
import json
import logging
import pathlib
from typing import Any


logger = logging.getLogger(__name__)

_BASELINES_PATH = pathlib.Path.home() / ".cohezion" / "degradation_baselines.json"


class DegradationObservabilityMixin:
    """Mixin that adds observability APIs to DegradationDetector.

    Expects the host class to have:
        self._baselines       — dict[str, MetricBaseline]
        self._alert_history   — list[DegradationAlert]
        self._call_count      — int
        self._snapshot_history — list[dict]
        self._max_snapshot_history — int
        self._composite_score — float | None
    """

    # ------------------------------------------------------------------
    # Health summary (CB6 dependency)
    # ------------------------------------------------------------------

    def get_health_summary(self) -> dict[str, bool | None]:
        """Tri-state health per monitored dimension.

        None   — grace period (baseline not yet established)
        True   — healthy
        False  — degraded
        """
        result: dict[str, bool | None] = {
            "cache": None,
            "token_efficiency": None,
            "coherence": None,
        }
        try:
            ch = self._baselines.get("cache_hit_rate")  # type: ignore[attr-defined]
            te = self._baselines.get("token_efficiency")  # type: ignore[attr-defined]
            co = self._baselines.get("coherence")  # type: ignore[attr-defined]
            if ch and ch.is_established:
                result["cache"] = ch.mean >= self.cache_hit_rate_threshold  # type: ignore[attr-defined]
            if te and te.is_established:
                result["token_efficiency"] = True  # degraded when alerts fired
            if co and co.is_established:
                result["coherence"] = co.mean >= self.coherence_threshold  # type: ignore[attr-defined]
            # Flip token_efficiency to False if any recent alert for it
            for alert in self._alert_history[-10:]:  # type: ignore[attr-defined]
                if alert.metric == "token_efficiency":
                    result["token_efficiency"] = False
                    break
        except Exception:
            pass
        return result

    # ------------------------------------------------------------------
    # Composite health score (CB10)
    # ------------------------------------------------------------------

    def get_composite_health_score(self) -> float | None:
        """Composite [0, 100] health score.

        None during the grace period (no baseline established yet).
        Averaged over established dimensions; 100 = perfect health.
        """
        try:
            return self._composite_score  # type: ignore[attr-defined]
        except Exception:
            return None

    def _compute_composite_score(self) -> float | None:
        """Compute current composite score from baselines. Called by check_degradation.

        Purely threshold-based: 100.0 when all monitored dimensions are healthy,
        deducted proportionally when below threshold. Does NOT count alert history
        so constitutional/ancillary alerts don't penalise an otherwise healthy run.
        Returns None during the grace period (no baseline established yet).
        """
        try:
            baselines = self._baselines  # type: ignore[attr-defined]
            established = [b for b in baselines.values() if b.is_established]
            if not established:
                return None

            score = 100.0
            ch = baselines.get("cache_hit_rate")
            if ch and ch.is_established:
                gap = max(0.0, self.cache_hit_rate_threshold - ch.mean)  # type: ignore[attr-defined]
                score -= gap * 100

            co = baselines.get("coherence")
            if co and co.is_established:
                gap = max(0.0, self.coherence_threshold - co.mean)  # type: ignore[attr-defined]
                score -= gap * 100

            return max(0.0, min(100.0, score))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Alert history (CB8, CB9)
    # ------------------------------------------------------------------

    def get_recent_alerts(self, n: int = 20) -> list:
        """Return up to *n* most recent DegradationAlert objects."""
        try:
            if n == 0:
                return []
            return list(self._alert_history[-n:])  # type: ignore[attr-defined]
        except Exception:
            return []

    def clear_alert_history(self) -> None:
        """Reset the bounded alert history (useful for test isolation)."""
        with contextlib.suppress(Exception):
            self._alert_history.clear()  # type: ignore[attr-defined]

    def get_alert_summary(self) -> dict[str, Any]:
        """Dashboard-level summary across all alert history.

        Returns dict with keys: total, by_severity, by_metric, most_recent_per_metric.
        Zero-state (no alerts) returns all-empty dicts and total=0.
        """
        summary: dict[str, Any] = {
            "total": 0,
            "by_severity": {},
            "by_metric": {},
            "most_recent_per_metric": {},
        }
        try:
            history = self._alert_history  # type: ignore[attr-defined]
            summary["total"] = len(history)
            for alert in history:
                sev = (
                    alert.severity.value
                    if hasattr(alert.severity, "value")
                    else str(alert.severity)
                )
                metric = alert.metric
                summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1
                summary["by_metric"][metric] = summary["by_metric"].get(metric, 0) + 1
                prev = summary["most_recent_per_metric"].get(metric)
                if prev is None or alert.timestamp > prev.get("timestamp", 0):
                    summary["most_recent_per_metric"][metric] = {
                        "message": alert.message,
                        "timestamp": alert.timestamp,
                        "severity": sev,
                    }
        except Exception:
            pass
        return summary

    # ------------------------------------------------------------------
    # Routing tier suggestion (CB12)
    # ------------------------------------------------------------------

    def suggest_routing_tier(self) -> str:
        """Return an actionable routing tier ('npu', 'igpu', or 'cpu').

        Maps composite health score to Triune Orchestrator tiers:
            ≥80  → 'npu'   (healthy — use fastest tier)
            50–79 → 'igpu'  (degraded — balanced tier)
            <50  → 'cpu'   (critical — most capable local tier)
        Grace period (composite_score=None) → 'igpu' (safe default).
        """
        try:
            score = self._composite_score  # type: ignore[attr-defined]
        except Exception:
            return "igpu"
        if score is None:
            return "igpu"
        if score >= 80:
            return "npu"
        if score >= 50:
            return "igpu"
        return "cpu"

    # ------------------------------------------------------------------
    # Snapshots (CB11)
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Capture current health state.  Returns exactly 6 required keys."""
        try:
            established = sum(
                1
                for b in self._baselines.values()
                if b.is_established  # type: ignore[attr-defined]
            )
            return {
                "call_count": self._call_count,  # type: ignore[attr-defined]
                "baselines_established": established,
                "health_summary": self.get_health_summary(),
                "composite_score": self.get_composite_health_score(),
                "alert_summary": self.get_alert_summary(),
                "health_trend": "stable",  # future: derive from snapshot history slope
            }
        except Exception:
            return {
                "call_count": 0,
                "baselines_established": 0,
                "health_summary": {},
                "composite_score": None,
                "alert_summary": {},
                "health_trend": "unknown",
            }

    def record_snapshot(self) -> dict[str, Any]:
        """Append current snapshot to bounded history and return it."""
        snap = self.snapshot()
        try:
            self._snapshot_history.append(snap)  # type: ignore[attr-defined]
            cap = self._max_snapshot_history  # type: ignore[attr-defined]
            if len(self._snapshot_history) > cap:  # type: ignore[attr-defined]
                self._snapshot_history[:] = self._snapshot_history[-cap:]  # type: ignore[attr-defined]
        except Exception:
            pass
        return snap

    @staticmethod
    def diff_snapshots(before: dict, after: dict) -> dict[str, Any]:
        """Pure dict transform: compute deltas between two snapshots.

        Returns zero deltas when snapshots are identical.
        score_delta is None when either snapshot has composite_score=None.
        """
        before_score = before.get("composite_score")
        after_score = after.get("composite_score")
        score_delta = None
        if before_score is not None and after_score is not None:
            score_delta = after_score - before_score

        before_alerts = before.get("alert_summary", {}).get("total", 0)
        after_alerts = after.get("alert_summary", {}).get("total", 0)

        before_health = before.get("health_summary", {})
        after_health = after.get("health_summary", {})
        health_changes: dict[str, Any] = {}
        for key in set(list(before_health.keys()) + list(after_health.keys())):
            bv = before_health.get(key)
            av = after_health.get(key)
            if bv != av:
                health_changes[key] = {"before": bv, "after": av}

        return {
            "score_delta": score_delta,
            "alert_count_delta": after_alerts - before_alerts,
            "call_count_delta": after.get("call_count", 0) - before.get("call_count", 0),
            "health_changes": health_changes,
        }

    # ------------------------------------------------------------------
    # Serialization (CB7)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable state for warm restart.

        Returns dict with keys: call_count, baselines.
        """
        try:
            baselines_data = {
                name: list(bl.samples)  # type: ignore[attr-defined]
                for name, bl in self._baselines.items()  # type: ignore[attr-defined]
            }
            return {
                "call_count": self._call_count,  # type: ignore[attr-defined]
                "baselines": baselines_data,
            }
        except Exception:
            return {"call_count": 0, "baselines": {}}

    @classmethod
    def from_dict(cls, state: dict[str, Any], **kwargs: Any) -> Any:
        """Restore baselines + call_count from serialized state.

        kwargs are forwarded to __init__ for threshold overrides.
        """
        instance = cls(**kwargs)
        try:
            instance._call_count = int(state.get("call_count", 0))
            for name, samples in state.get("baselines", {}).items():
                if name in instance._baselines:
                    instance._baselines[name].samples = [float(s) for s in samples]
        except Exception:
            pass
        return instance

    def end_session(self) -> None:
        """Auto-save baselines to disk (~/.cohezion/degradation_baselines.json)."""
        try:
            _BASELINES_PATH.parent.mkdir(parents=True, exist_ok=True)
            _BASELINES_PATH.write_text(json.dumps(self.to_dict(), indent=2))
            logger.debug("DegradationDetector: baselines saved to %s", _BASELINES_PATH)
        except Exception:
            logger.debug("DegradationDetector: baseline save failed (non-blocking)")

    def start_session(self) -> None:
        """Auto-restore baselines from disk (~/.cohezion/degradation_baselines.json)."""
        try:
            if _BASELINES_PATH.exists():
                state = json.loads(_BASELINES_PATH.read_text())
                self._call_count = int(state.get("call_count", 0))
                for name, samples in state.get("baselines", {}).items():
                    if name in self._baselines:
                        self._baselines[name].samples = [float(s) for s in samples]
                logger.debug("DegradationDetector: baselines restored from %s", _BASELINES_PATH)
        except Exception:
            logger.debug("DegradationDetector: baseline restore failed (non-blocking)")
