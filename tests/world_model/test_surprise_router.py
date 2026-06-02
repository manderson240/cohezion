"""Tests for the Active-Inference SurpriseRouter (world_model/surprise_router.py).

Covers the control rule (low surprise -> exploit/cheap tier, high -> explore/capable tier),
adaptive EWMA normalization (same absolute value classified differently as scale shifts),
hysteresis (no flapping in the dead-band), and the live journey-point reader (None when the
jepa_surprise enrichment is absent -- a no-op, never a fabricated decision).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cohezion.world_model.surprise_router import (
    ActionMode,
    SurpriseDecision,
    SurpriseRouter,
)


# -- construction / validation -------------------------------------------------


def test_rejects_out_of_range_params():
    with pytest.raises(ValueError):
        SurpriseRouter(explore_threshold=1.5)
    with pytest.raises(ValueError):
        SurpriseRouter(hysteresis=0.5)
    with pytest.raises(ValueError):
        SurpriseRouter(ewma_alpha=0.0)


def test_cold_start_scale_is_none():
    assert SurpriseRouter().scale is None


# -- core control rule ---------------------------------------------------------


def test_steady_state_is_exploit_npu():
    """A constant surprise stream sits at the EWMA mean (norm ~0.5) -> exploit, mid/low tier."""
    r = SurpriseRouter()
    d = None
    for _ in range(10):
        d = r.observe(0.5)
    assert isinstance(d, SurpriseDecision)
    # constant input => surprise == scale => normalized == 0.5 (the 2x-scale center)
    assert d.normalized == pytest.approx(0.5, abs=0.05)
    assert d.mode is ActionMode.EXPLOIT  # 0.5 < threshold 0.6 - hysteresis 0.1 = 0.5 boundary


def test_high_surprise_spike_triggers_explore_and_escalates_tier():
    r = SurpriseRouter()
    for _ in range(10):
        r.observe(0.1)  # establish a low scale
    spike = r.observe(5.0)  # >> running scale
    assert spike.normalized == 1.0  # clamped
    assert spike.mode is ActionMode.EXPLORE
    assert spike.tier == "cpu"  # high band -> most capable local tier


def test_low_surprise_after_high_scale_exploits_npu():
    r = SurpriseRouter()
    for _ in range(10):
        r.observe(5.0)  # establish a high scale
    low = r.observe(0.01)  # tiny relative to scale
    assert low.normalized < 1.0 / 3.0
    assert low.tier == "npu"
    assert low.mode is ActionMode.EXPLOIT


# -- adaptive normalization (the key robustness property) ----------------------


def test_same_absolute_surprise_classified_by_context_not_magnitude():
    """The SAME raw value is 'high' against a low scale and 'low' against a high scale."""
    low_scale = SurpriseRouter()
    for _ in range(10):
        low_scale.observe(0.05)
    against_low = low_scale.observe(1.0)

    high_scale = SurpriseRouter()
    for _ in range(10):
        high_scale.observe(10.0)
    against_high = high_scale.observe(1.0)

    # identical raw surprise, opposite classifications -> normalization is contextual
    assert against_low.normalized > against_high.normalized
    assert against_low.tier == "cpu"
    assert against_high.tier == "npu"


def test_tier_is_monotonic_in_normalized_surprise():
    r = SurpriseRouter()
    r.observe(1.0)  # seed scale
    rank = {"npu": 0, "igpu": 1, "cpu": 2}
    prev = -1
    for s in (0.01, 0.5, 1.0, 2.0, 10.0):
        d = SurpriseRouter()
        d.observe(1.0)  # identical seed so scale matches
        dec = d.observe(s)
        assert rank[dec.tier] >= prev or s < 1.0  # capability never decreases with surprise
        prev = max(prev, rank[dec.tier])


# -- hysteresis ----------------------------------------------------------------


def test_hysteresis_prevents_flapping_in_deadband():
    """Values oscillating inside [threshold-hyst, threshold+hyst] hold the last mode."""
    r = SurpriseRouter(explore_threshold=0.6, hysteresis=0.15)
    # Drive firmly into EXPLORE first.
    for _ in range(10):
        r.observe(0.1)
    r.observe(10.0)
    assert r._last_mode is ActionMode.EXPLORE
    # Now feed values that normalize into the dead-band; mode must stay EXPLORE (no flap).
    held = r.observe(r.scale * 1.1)  # normalized ~0.55, inside [0.45, 0.75]
    assert 0.45 <= held.normalized <= 0.75
    assert held.mode is ActionMode.EXPLORE


def test_zero_hysteresis_switches_at_threshold():
    r = SurpriseRouter(explore_threshold=0.5, hysteresis=0.0)
    r.observe(1.0)  # scale=1.0
    below = r.observe(0.8)  # norm 0.4 < 0.5
    assert below.mode is ActionMode.EXPLOIT
    above = r.observe(1.4)  # norm 0.7 > 0.5
    assert above.mode is ActionMode.EXPLORE


# -- live journey-point reader -------------------------------------------------


def test_decide_from_point_reads_metadata():
    r = SurpriseRouter()
    r.observe(0.1)  # seed scale low
    point = SimpleNamespace(metadata={"jepa_surprise": 5.0})
    dec = r.decide_from_point(point)
    assert dec is not None
    assert dec.mode is ActionMode.EXPLORE


def test_decide_from_point_none_when_no_surprise():
    r = SurpriseRouter()
    assert r.decide_from_point(SimpleNamespace(metadata={})) is None
    assert r.decide_from_point(SimpleNamespace(metadata={"other": 1})) is None
    assert r.decide_from_point(SimpleNamespace()) is None  # no metadata attr
    assert r.decide_from_point(object()) is None


def test_decision_to_dict_roundtrip():
    r = SurpriseRouter()
    d = r.observe(0.5)
    out = d.to_dict()
    assert set(out) == {"mode", "tier", "surprise", "normalized", "rationale"}
    assert out["mode"] in {"explore", "exploit"}
    assert out["tier"] in {"npu", "igpu", "cpu"}
