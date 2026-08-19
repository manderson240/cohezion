"""OSW1-OSW3: the oscillation signal must be CONSUMED by DegradationDetector, not just defined.

Per .claude/rules/verification-depth.md corrective #2: a capability is wired only when a
production consumer reads it and acts on it. These tests fail if `_refresh_oscillation` is
never called from `check_degradation`.
"""

from __future__ import annotations

import numpy as np

from cohezion.compound.degradation_detector import DegradationDetector
from cohezion.compound.oscillation_detector import OSCILLATION_THRESHOLD


N = 20
_PERIOD_8 = list(0.65 + 0.25 * np.sin(2 * np.pi * np.arange(N) / 8))


def _feed(detector: DegradationDetector, series: list[float]) -> list:
    alerts: list = []
    for c in series:
        alerts.extend(detector.check_degradation({"mean_coherence": float(c)}))
    return alerts


class TestOSW1SignalIsConsumed:
    def test_thrashing_coherence_stream_sets_hidden_thrash(self) -> None:
        """THE discriminating test. A detector that defines the method but never calls it
        from check_degradation leaves hidden_thrash False forever."""
        d = DegradationDetector()
        _feed(d, _PERIOD_8)
        reading = d.get_oscillation_reading()
        assert reading["hidden_thrash"] is True, (
            "oscillation signal is DORMANT — check_degradation never refreshed it"
        )
        assert reading["oscillation_score"] > OSCILLATION_THRESHOLD

    def test_healthy_drift_stream_does_not_set_hidden_thrash(self) -> None:
        """Discriminating the other way: an always-True consumer would pass the test above."""
        rng = np.random.default_rng(3)
        drift = list(np.clip(0.7 + np.cumsum(rng.normal(0, 0.04, N)), 0, 1))
        d = DegradationDetector()
        _feed(d, drift)
        assert d.get_oscillation_reading()["hidden_thrash"] is False

    def test_oscillation_baseline_accumulates_samples(self) -> None:
        d = DegradationDetector()
        _feed(d, _PERIOD_8)
        assert len(d._baselines["oscillation"].samples) == N


class TestOSW2ObserveOnly:
    """The signal must NOT gate, alert, or route. If any of these start failing, the
    promotion from observe-only to acting was made without recalibrating the threshold."""

    def test_thrash_emits_no_alert(self) -> None:
        d = DegradationDetector()
        alerts = _feed(d, _PERIOD_8)
        assert [a for a in alerts if "oscillat" in a.metric.lower()] == []

    def test_thrash_does_not_change_routing_tier(self) -> None:
        thrash = DegradationDetector()
        _feed(thrash, _PERIOD_8)
        calm = DegradationDetector()
        _feed(calm, [float(np.mean(_PERIOD_8))] * N)
        assert thrash.suggest_routing_tier() == calm.suggest_routing_tier()

    def test_oscillation_absent_from_health_verdicts(self) -> None:
        d = DegradationDetector()
        _feed(d, _PERIOD_8)
        assert "oscillation" not in d._current_health


class TestOSW3FrozenSurfaces:
    """CB7 to_dict is a frozen top-level shape; adding a baseline key must not disturb it."""

    def test_to_dict_top_level_keys_unchanged(self) -> None:
        d = DegradationDetector()
        _feed(d, _PERIOD_8)
        assert set(d.to_dict()) == {"call_count", "baselines", "skill_drift"}

    def test_round_trip_survives_oscillation_baseline(self) -> None:
        d = DegradationDetector()
        _feed(d, _PERIOD_8)
        restored = DegradationDetector.from_dict(d.to_dict())
        assert restored._call_count == N

    def test_no_coherence_metric_leaves_reading_at_default(self) -> None:
        d = DegradationDetector()
        for _ in range(N):
            d.check_degradation({"success_rate": 0.9})
        assert d.get_oscillation_reading()["oscillation_score"] == 0.0
