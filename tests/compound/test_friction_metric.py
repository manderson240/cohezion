"""Tests for the Φ friction metric (observe-only active-inference bottleneck signal).

Spec: vault/research/2026-07-11-friction-metric-and-physics-spec-mapping.md
"""

from __future__ import annotations

import pytest

from cohezion.compound.degradation_detector import DegradationDetector
from cohezion.compound.friction_metric import FrictionMetric, FrictionReading


class TestFrictionMetricComposite:
    def test_phi_bounded_0_1(self):
        """Φ stays in [0,1] across arbitrary (including extreme) inputs."""
        fm = FrictionMetric()
        for s, d, g, q in [(0, 0, 0, 0), (1e6, 1.0, 1e6, 0.0), (5, -3, 5, 99)]:
            r = fm.compute(surprise=s, phase_divergence=d, entropy_production=g, quality_delta=q)
            assert 0.0 <= r.phi <= 1.0

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValueError, match="must sum to"):
            FrictionMetric(w_surprise=0.5, w_divergence=0.5, w_entropy=0.5, w_stagnation=0.5)

    def test_phase_divergence_term_isolated(self):
        """With all weight on divergence, Φ equals the (already [0,1]) divergence input."""
        fm = FrictionMetric(w_surprise=0.0, w_divergence=1.0, w_entropy=0.0, w_stagnation=0.0)
        assert fm.compute(
            surprise=0, phase_divergence=0.73, entropy_production=0, quality_delta=1.0
        ).phi == pytest.approx(0.73)

    def test_stagnation_is_conjunctive_gated_by_surprise(self):
        """A quality plateau counts as friction ONLY when surprise is also high."""
        fm = FrictionMetric(w_surprise=0.0, w_divergence=0.0, w_entropy=0.0, w_stagnation=1.0)
        # Warm surprise history high, then LOW surprise → gate closed → plateau ignored.
        fm.compute(surprise=100.0, phase_divergence=0, entropy_production=0, quality_delta=0.0)
        closed = fm.compute(
            surprise=1.0, phase_divergence=0, entropy_production=0, quality_delta=0.0
        )
        assert closed.surprise < 0.5
        assert closed.stagnation == 0.0 and closed.phi == 0.0
        # High surprise + plateau → gate open → stagnation contributes fully.
        opened = fm.compute(
            surprise=1e6, phase_divergence=0, entropy_production=0, quality_delta=0.0
        )
        assert opened.surprise >= 0.5
        assert opened.stagnation == pytest.approx(1.0) and opened.phi == pytest.approx(1.0)


class TestFrictionHysteresis:
    def test_enters_friction_only_on_sustained_high_phi(self):
        """Regime flips to 'friction' only after `sustain` consecutive over-threshold cycles."""
        fm = FrictionMetric(
            w_surprise=0.0, w_divergence=1.0, w_entropy=0.0, w_stagnation=0.0, sustain=2
        )

        def step(d):
            return fm.compute(
                surprise=0, phase_divergence=d, entropy_production=0, quality_delta=1.0
            ).regime

        assert step(0.9) == "navigate"  # streak 1, not yet sustained
        assert step(0.9) == "friction"  # streak 2 → flip

    def test_single_spike_does_not_flip(self):
        """An isolated spike (not sustained) never enters friction — anti-chatter."""
        fm = FrictionMetric(
            w_surprise=0.0, w_divergence=1.0, w_entropy=0.0, w_stagnation=0.0, sustain=2
        )
        regimes = [
            fm.compute(
                surprise=0, phase_divergence=d, entropy_production=0, quality_delta=1.0
            ).regime
            for d in (0.9, 0.5, 0.9, 0.5, 0.9)  # alternating, never 2 in a row
        ]
        assert regimes == ["navigate"] * 5

    def test_dead_band_holds_regime(self):
        """Once in friction, Φ inside the dead-band (0.4–0.6) does NOT exit; <0.4 does."""
        fm = FrictionMetric(
            w_surprise=0.0, w_divergence=1.0, w_entropy=0.0, w_stagnation=0.0, sustain=2
        )
        fm.compute(surprise=0, phase_divergence=0.9, entropy_production=0, quality_delta=1.0)
        assert (
            fm.compute(
                surprise=0, phase_divergence=0.9, entropy_production=0, quality_delta=1.0
            ).regime
            == "friction"
        )
        # inside dead-band → stays friction
        assert (
            fm.compute(
                surprise=0, phase_divergence=0.5, entropy_production=0, quality_delta=1.0
            ).regime
            == "friction"
        )
        # below exit threshold → back to navigate
        assert (
            fm.compute(
                surprise=0, phase_divergence=0.3, entropy_production=0, quality_delta=1.0
            ).regime
            == "navigate"
        )


class TestDegradationDetectorComputeFriction:
    def test_additive_accessor_and_cb_shapes_intact(self):
        """compute_friction is additive: records a friction baseline, breaks no CB5–16 shape."""
        d = DegradationDetector()
        r = d.compute_friction(
            surprise=1.0, phase_divergence=0.2, entropy_production=0.5, quality_delta=0.3
        )
        assert isinstance(r, FrictionReading) and 0.0 <= r.phi <= 1.0
        assert "friction" in d._baselines  # 10th baseline created lazily

        dd = d.to_dict()  # CB7: top-level shape unchanged, friction nested under baselines
        assert {"call_count", "baselines"} <= set(dd.keys())
        assert "friction" in dd["baselines"]

        snap = d.snapshot()  # CB11: still exactly 6 keys
        assert len(snap) == 6
        al = d.get_alert_summary()  # CB9: keys intact
        assert {"total", "by_severity", "by_metric", "most_recent_per_metric"} <= set(al.keys())

    def test_friction_does_not_bump_call_count(self):
        """Observe-only: computing friction is not a degradation check (no call_count change)."""
        d = DegradationDetector()
        before = d.to_dict()["call_count"]
        d.compute_friction(
            surprise=2.0, phase_divergence=0.1, entropy_production=0.2, quality_delta=0.5
        )
        assert d.to_dict()["call_count"] == before
