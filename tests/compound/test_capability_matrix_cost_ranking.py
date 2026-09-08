"""recommend_for_task must not be blind to cost.

Measured 2026-08-27: ranking was ``affinity + quality_score`` with no cost or
speed term, so ``recommend_for_task("classification")`` put a speed_tier-5,
262k-context coder model first -- the exact task the quarter-on-a-string
protocol routes to the cheapest lane.

Scope note, deliberately narrow: the fix is a *tie-break*, not a cost/quality
exchange rate. Choosing a weight large enough to trade quality for cost is a
routing-policy decision that needs benchmarking evidence (same gate as the
roster migration), so the default weight is small by design and these tests
assert only what is defensible without that evidence:

  * among equal-scoring candidates, the cheaper tier ranks first
  * a real quality gap still wins over a tier difference

A separate, larger finding stands: no model carries a "classification" affinity
at all, so that task falls back to quality-only ranking. That is a data gap in
the affinity map, not a ranking bug, and is reported rather than patched here.
"""

from __future__ import annotations

from cohezion.compound.capability_matrix import CapabilityEntry, CapabilityMatrix


def _entry(entity_id: str, quality: float, tier: int, affinity: float) -> CapabilityEntry:
    return CapabilityEntry(
        entity_type="model",
        entity_id=entity_id,
        capabilities=["coding"],
        quality_score=quality,
        speed_tier=tier,
        success_rate=0.0,
        affinity={"coding": affinity},
        last_assessed="2026-08-27",
        source="static",
        metadata={"context_length": 1024, "tps": 0.0, "latency_ms": 0.0},
    )


def _matrix(*entries: CapabilityEntry) -> CapabilityMatrix:
    matrix = CapabilityMatrix()
    matrix._entries = {entry.entity_id: entry for entry in entries}
    return matrix


def test_cheaper_tier_wins_when_scores_are_equal() -> None:
    """DISCRIMINATING: red under pure ``affinity + quality`` ranking.

    Both candidates score identically on affinity and quality; only speed_tier
    separates them. A cost-blind ranking leaves them in arbitrary order.
    """
    matrix = _matrix(
        _entry("expensive", quality=0.8, tier=5, affinity=0.9),
        _entry("cheap", quality=0.8, tier=1, affinity=0.9),
    )
    assert matrix.recommend_for_task("coding")[0].entity_id == "cheap"


def test_real_quality_gap_still_beats_a_tier_difference() -> None:
    """Guards the over-correction: cost must not dominate capability."""
    matrix = _matrix(
        _entry("capable", quality=1.0, tier=5, affinity=0.9),
        _entry("weak", quality=0.4, tier=1, affinity=0.9),
    )
    assert matrix.recommend_for_task("coding")[0].entity_id == "capable"


def test_cost_weight_is_tunable_through_constraints() -> None:
    """A caller with evidence can trade cost against quality explicitly."""
    entries = (
        _entry("capable", quality=1.0, tier=5, affinity=0.9),
        _entry("weak", quality=0.4, tier=1, affinity=0.9),
    )
    aggressive = _matrix(*entries).recommend_for_task("coding", {"cost_weight": 1.0})
    assert aggressive[0].entity_id == "weak"


def test_ranking_is_still_descending_overall() -> None:
    """The list stays sorted best-first; only the key changed."""
    matrix = _matrix(
        _entry("a", quality=0.4, tier=3, affinity=0.1),
        _entry("b", quality=1.0, tier=1, affinity=0.9),
        _entry("c", quality=0.6, tier=2, affinity=0.5),
    )
    assert [e.entity_id for e in matrix.recommend_for_task("coding")] == ["b", "c", "a"]


def test_cost_term_cannot_reorder_a_gap_larger_than_the_weight() -> None:
    """Pins the actual boundary, rather than trusting the prose.

    Adversarial review (glm-5.3-flash, 2026-08-27) correctly refuted the
    unqualified claim "tier never overrides quality": the tier penalty spans at
    most ``cost_weight``, so it CAN reorder pairs closer than that. A gap just
    above the weight must survive the maximum possible tier penalty.
    """
    from cohezion.compound.capability_matrix import _DEFAULT_COST_WEIGHT

    gap = _DEFAULT_COST_WEIGHT * 1.5
    matrix = _matrix(
        _entry("slightly_better", quality=0.5 + gap, tier=5, affinity=0.5),
        _entry("cheapest", quality=0.5, tier=1, affinity=0.5),
    )
    assert matrix.recommend_for_task("coding")[0].entity_id == "slightly_better"


def test_cost_term_does_reorder_a_gap_smaller_than_the_weight() -> None:
    """The honest other half: inside the weight, tier DOES win.

    This is a documented property, not a defect -- but it must be pinned, so
    nobody later reads the docstring as an absolute guarantee.
    """
    from cohezion.compound.capability_matrix import _DEFAULT_COST_WEIGHT

    gap = _DEFAULT_COST_WEIGHT * 0.5
    matrix = _matrix(
        _entry("slightly_better", quality=0.5 + gap, tier=5, affinity=0.5),
        _entry("cheapest", quality=0.5, tier=1, affinity=0.5),
    )
    assert matrix.recommend_for_task("coding")[0].entity_id == "cheapest"


def test_existing_constraints_still_filter() -> None:
    """min_quality filtering is unchanged by the new ranking key."""
    matrix = _matrix(
        _entry("high", quality=1.0, tier=5, affinity=0.9),
        _entry("low", quality=0.4, tier=1, affinity=0.9),
    )
    recs = matrix.recommend_for_task("coding", {"min_quality": 0.9})
    assert [e.entity_id for e in recs] == ["high"]
