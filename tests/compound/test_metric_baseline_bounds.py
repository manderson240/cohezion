"""MB1: MetricBaseline.value_bounds must clamp trend_value() for bounded metrics.

`trend_value()` fits a degree-1 polynomial and extrapolates. For metrics defined on [0, 1]
that projection can leave the range entirely. Measured before the fix, at horizon=1 — the
ONLY horizon production uses:

    coherence   [0.9, 0.7, 0.5, 0.3, 0.1]      -> -0.1000
    coherence   [0.30, 0.22, 0.14, 0.06, 0.02] -> -0.0680
    success     [0.2, 0.45, 0.7, 0.9, 0.98]    -> +1.2490
    quality     [0.5, 0.7, 0.85, 0.95, 0.99]   -> +1.1670

check_degradation() uses trend_value(1) as the comparison BASELINE, so a baseline below the
metric's own floor makes `current < baseline` unsatisfiable and silently suppresses the alert.

harness.md documented this invariant as implemented with "12 passed". It was not: `value_bounds`
had zero occurrences in src on both HEAD and origin/main, and zero references in the test suite.
This file makes the documented invariant true.
"""

from __future__ import annotations

from cohezion.compound.degradation_detector import DegradationDetector, MetricBaseline

_DECLINE = [0.9, 0.7, 0.5, 0.3, 0.1]
_CLIMB = [0.2, 0.45, 0.7, 0.9, 0.98]


class TestValueBoundsClamp:
    def test_declining_bounded_metric_never_projects_below_floor(self) -> None:
        b = MetricBaseline("coherence", samples=list(_DECLINE), value_bounds=(0.0, 1.0))
        assert b.trend_value(1) >= 0.0

    def test_climbing_bounded_metric_never_projects_above_ceiling(self) -> None:
        b = MetricBaseline("success_rate", samples=list(_CLIMB), value_bounds=(0.0, 1.0))
        assert b.trend_value(1) <= 1.0

    def test_clamp_holds_at_longer_horizons(self) -> None:
        b = MetricBaseline("coherence", samples=list(_DECLINE), value_bounds=(0.0, 1.0))
        assert all(0.0 <= b.trend_value(h) <= 1.0 for h in (1, 3, 5, 10, 50))

    def test_in_range_projection_is_left_alone(self) -> None:
        """Discriminating: an impl that clamps to a constant would fail this."""
        b = MetricBaseline("coherence", samples=[0.5, 0.5, 0.5, 0.5], value_bounds=(0.0, 1.0))
        assert abs(b.trend_value(1) - 0.5) < 1e-9

    def test_unbounded_metric_can_extrapolate_outside_unit_interval(self) -> None:
        """THE discriminating test: proves the clamp is SELECTIVE, not applied globally.

        A wrong implementation that clamps every metric to [0,1] would fail here, and would
        silently corrupt token_efficiency (tokens/sec, legitimately >> 1).
        """
        b = MetricBaseline("token_efficiency", samples=[10.0, 20.0, 30.0, 40.0])
        assert b.trend_value(1) > 1.0, "unbounded metric was clamped — clamp is not selective"

    def test_default_is_none_so_existing_behaviour_is_unchanged(self) -> None:
        assert MetricBaseline("anything").value_bounds is None

    def test_fallback_to_mean_is_also_clamped(self) -> None:
        """<2 samples falls back to mean; mean of in-range samples is in range, but the
        clamp must not be bypassed on that path."""
        b = MetricBaseline("coherence", samples=[0.4], value_bounds=(0.0, 1.0))
        assert 0.0 <= b.trend_value(1) <= 1.0


class TestDetectorWiring:
    """The field must be CONSUMED by the detector, not merely available (wiring discipline)."""

    def test_bounded_baselines_are_wired(self) -> None:
        d = DegradationDetector()
        for name in ("cache_hit_rate", "coherence", "success_rate", "quality_score",
                     "jepa_coherence"):
            assert d._baselines[name].value_bounds == (0.0, 1.0), f"{name} not wired"

    def test_unbounded_baselines_are_left_unbounded(self) -> None:
        """Discriminating: a blanket wiring loop would fail this."""
        d = DegradationDetector()
        for name in ("token_efficiency", "duration_seconds", "token_surprisal"):
            assert d._baselines[name].value_bounds is None, f"{name} wrongly bounded"

    def test_wired_detector_suppresses_the_measured_defect(self) -> None:
        """End-to-end: the exact series that produced -0.1000 before the fix."""
        d = DegradationDetector()
        for s in _DECLINE:
            d._baselines["coherence"].add_sample(s)
        assert d._baselines["coherence"].trend_value(1) >= 0.0
