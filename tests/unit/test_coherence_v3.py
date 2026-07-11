"""Tests for the ADDITIVE, OFF-by-default coherence-v3 machinery.

All grader/entailment calls are mocked — no test touches :13305. Covers the Opus
change-set gates: OFF-by-default equivalence to executor Step 5.8, the multiplicative
form's variance preservation (F4), the verbal/CB14 faithfulness gate (F2/CB14),
spine_liveness_ok (gate 0 / F1), and workspace_occupancy independence (F6).
"""

from __future__ import annotations

import statistics

import pytest

from cohezion.compound.coherence_v3 import (
    CoherenceV3Result,
    _cb14_cites_metrics,
    coherence_v1,
    compute_coherence,
    compute_coherence_v3,
    spine_liveness_ok,
    workspace_occupancy,
)


def _const_grader(value: float):
    return lambda task, output: value


def _const_entail(value: float):
    return lambda insight, metrics: value


# ---------------------------------------------------------------------------
# OFF by default == executor Step 5.8 formula (the core non-regression contract)
# ---------------------------------------------------------------------------
def _step58_reference(success: bool, metrics: dict) -> float:
    """Independent inline replication of executor.py Step 5.8 (lines 1286-1300)."""
    components = [0.7 if success else 0.2]
    components.append(metrics.get("anomaly_score", 1.0))
    align = metrics.get("alignment", {})
    if align:
        components.append(align.get("intent_match", 0.5))
    return sum(components) / len(components)


@pytest.mark.parametrize(
    "success,metrics",
    [
        (True, {}),
        (False, {}),
        (True, {"anomaly_score": 0.4}),
        (False, {"anomaly_score": 0.85}),
        (True, {"anomaly_score": 0.9, "alignment": {"intent_match": 0.6}}),
        (True, {"anomaly_score": 0.9, "alignment": {}}),  # empty dict → not appended
        (True, {"alignment": {"intent_match": 0.3}}),  # anomaly defaults to 1.0
    ],
)
def test_off_by_default_reproduces_step58(success, metrics):
    """enable_coherence_v3=False reproduces the current Step 5.8 formula exactly."""
    expected = _step58_reference(success, metrics)
    got = compute_coherence(success=success, metrics=metrics, enable_coherence_v3=False)
    assert got == expected
    # coherence_v1 is the same path.
    assert coherence_v1(success, metrics) == expected


def test_off_by_default_ignores_grader_and_entail():
    """With the flag off, grader/entail_fn are never consulted — value is pure Step 5.8."""

    def _boom(*a, **k):  # would raise if called
        raise AssertionError("grader/entail must not run on the OFF path")

    got = compute_coherence(
        success=True,
        metrics={"anomaly_score": 0.5},
        enable_coherence_v3=False,
        grader=_boom,
        entail_fn=_boom,
    )
    assert got == _step58_reference(True, {"anomaly_score": 0.5})


def test_v3_requires_grader_and_entail():
    """A v3 request without the injected callables is a loud caller error, not a silent fallback."""
    with pytest.raises(ValueError):
        compute_coherence(success=True, metrics={}, enable_coherence_v3=True)
    with pytest.raises(ValueError):
        compute_coherence(success=True, metrics={}, coherence_version=2, grader=_const_grader(0.8))


def test_coherence_version_2_selects_v3():
    """coherence_version==2 activates v3 even when enable flag is left False."""
    got = compute_coherence(
        success=True,
        metrics={"anomaly_score": 1.0, "quality_score": 0.8},
        task="reason about X",
        output_text="a considered answer",
        learning="quality_score was 0.8",
        coherence_version=2,
        grader=_const_grader(0.8),
        entail_fn=_const_entail(0.95),
    )
    off = compute_coherence(success=True, metrics={"anomaly_score": 1.0})
    assert got != off  # v3 path produced a genuinely different value


# ---------------------------------------------------------------------------
# Multiplicative form (Opus F4): variance preserved, NOT re-saturated
# ---------------------------------------------------------------------------
def test_multiplicative_form_preserves_variance_for_healthy_runs():
    """Healthy runs (health≈1, verbal≈1) must NOT collapse to a constant final value."""
    spines = [s / 100 for s in range(30, 96, 5)]  # varied genuine difficulty
    metrics = {"anomaly_score": 1.0, "quality_score": 0.85}
    entail = _const_entail(0.95)
    finals = [
        compute_coherence_v3(
            task="t",
            output_text="o",
            learning="quality_score 0.85",  # cites metric → CB14 passes → verbal=entail
            metrics=metrics,
            success=True,
            grader=_const_grader(s),
            entail_fn=entail,
        ).final_coherence
        for s in spines
    ]
    # Variance survives the two near-constant gate factors (F4: var ≈ 0.8·var(base)).
    assert statistics.pstdev(finals) > 0.10
    assert max(finals) - min(finals) > 0.40
    # No single 3-decimal value dominates (the v1 saturation failure mode).
    rounded = [round(f, 3) for f in finals]
    assert len(set(rounded)) >= len(spines) - 1


def test_multiplicative_result_fields_in_range():
    res = compute_coherence_v3(
        task="t",
        output_text="o",
        learning="quality_score 0.8",
        metrics={"anomaly_score": 1.0, "quality_score": 0.8},
        success=True,
        grader=_const_grader(0.8),
        entail_fn=_const_entail(0.9),
    )
    assert isinstance(res, CoherenceV3Result)
    for v in (res.final_coherence, res.base, res.health, res.verbal, res.spine, res.depth):
        assert 0.0 <= v <= 1.0
    assert res.coherence_version == 2


# ---------------------------------------------------------------------------
# Verbal / faithfulness gate (F2 + CB14 reuse)
# ---------------------------------------------------------------------------
def test_verbal_gate_blocks_confabulated_insight():
    """A confabulated self-report scores below a faithful one at identical spine/health."""
    metrics = {"anomaly_score": 1.0, "quality_score": 0.8, "tokens_used": 100}
    grader = _const_grader(0.8)
    # entail_fn is generous for BOTH — the CB14 floor is what separates them.
    entail = _const_entail(0.95)
    faithful = compute_coherence_v3(
        task="t",
        output_text="o",
        learning="quality_score was 0.8 over 100 tokens",  # cites real metrics
        metrics=metrics,
        success=True,
        grader=grader,
        entail_fn=entail,
    )
    confab = compute_coherence_v3(
        task="t",
        output_text="o",
        learning="the model achieved flawless perfect mastery of everything",  # no metric
        metrics=metrics,
        success=True,
        grader=grader,
        entail_fn=entail,
    )
    assert confab.final_coherence < faithful.final_coherence
    assert confab.verbal == 0.0  # CB14 floor fired
    assert faithful.verbal == pytest.approx(0.95)


def test_verbal_gate_respects_entailment_judge():
    """When CB14 passes (numbers cited), the injected entailment judge drives verbal."""
    metrics = {"anomaly_score": 1.0, "quality_score": 0.8, "tokens_used": 100}
    grader = _const_grader(0.8)
    low = compute_coherence_v3(
        task="t",
        output_text="o",
        learning="ran in 100 tokens",  # cites tokens → CB14 passes
        metrics=metrics,
        success=True,
        grader=grader,
        entail_fn=_const_entail(0.10),  # judge says NOT faithful
    )
    high = compute_coherence_v3(
        task="t",
        output_text="o",
        learning="ran in 100 tokens",
        metrics=metrics,
        success=True,
        grader=grader,
        entail_fn=_const_entail(0.95),
    )
    assert low.verbal == pytest.approx(0.10)
    assert high.verbal == pytest.approx(0.95)
    assert low.final_coherence < high.final_coherence


def test_cb14_reuse_executes():
    """The CB14 machinery is genuinely reused (not duplicated): it separates cite vs no-cite."""
    metrics = {"quality_score": 0.8, "tokens_used": 100}
    assert _cb14_cites_metrics("quality_score was 0.8", metrics) is True
    assert _cb14_cites_metrics("a flawless triumph with no numbers", metrics) is False


# ---------------------------------------------------------------------------
# Gate 0 — spine liveness (F1)
# ---------------------------------------------------------------------------
def test_spine_liveness_rejects_degenerate_constant():
    assert spine_liveness_ok([0.5] * 30) is False  # 1 distinct value
    assert spine_liveness_ok([0.0] * 40) is False


def test_spine_liveness_rejects_dominant_value():
    # 24/40 = 60% share of a single value → fails max_share even with enough distinct values.
    samples = [0.5] * 24 + [i / 100 for i in range(1, 17)]
    assert len({round(s, 3) for s in samples}) >= 8
    assert spine_liveness_ok(samples) is False


def test_spine_liveness_rejects_too_few_samples():
    assert spine_liveness_ok([i / 100 for i in range(29)]) is False  # < 30


def test_spine_liveness_accepts_varied_signal():
    samples = [i / 100 for i in range(30, 90, 2)]  # 30 distinct values, each ~3.3%
    assert len(samples) >= 30
    assert spine_liveness_ok(samples) is True


# ---------------------------------------------------------------------------
# workspace_occupancy — the SEPARATE balance scalar (F6)
# ---------------------------------------------------------------------------
def test_occupancy_degenerate_vs_varied():
    assert workspace_occupancy("aaa aaa aaa aaa") == 0.0  # one distinct token
    assert workspace_occupancy("") == 0.0
    varied = workspace_occupancy("the quick brown fox jumps over a lazy dog")
    assert varied > 0.9  # all-distinct tokens → near-max normalized entropy
    for text in ("aaa aaa", "the quick brown fox", "x y z"):
        assert 0.0 <= workspace_occupancy(text) <= 1.0


def test_occupancy_independent_of_quality():
    """Occupancy measures topical spread, not quality — it is not the coherence scalar.

    A repetitive but 'successful' output has low occupancy; a varied output has high
    occupancy, regardless of any coherence inputs. This is the independence the sibling
    scalar must have (design §6 / F6 gate f-i).
    """
    repetitive = workspace_occupancy("done done done done done")
    exploratory = workspace_occupancy("explored kriging particle filter beam search entropy")
    assert repetitive < exploratory
    # Same text always yields the same occupancy (pure function of the string).
    assert workspace_occupancy("alpha beta gamma") == workspace_occupancy("alpha beta gamma")
