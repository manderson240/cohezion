"""Item 106: memory_utilization(layer_counts) — TDD red→green.

``memory_utilization(layer_counts, *, floor, under_distilled_threshold)`` classifies
SurrealDB memory-layer record counts into dormant/sparse/healthy and flags the
raw:distilled ratio when it indicates a distillation bottleneck.

Discriminating tests — each kills a plausible wrong implementation:
  - zero-count is `dormant`, NOT `sparse`                → test_zero_count_is_dormant
  - 0<count<floor is `sparse`, NOT dormant or healthy    → test_below_floor_is_sparse
  - count>=floor is `healthy`                            → test_above_floor_is_healthy
  - dormant and sparse are DISJOINT                      → test_dormant_not_in_sparse
  - huge ratio → under_distilled=True                    → test_under_distilled_huge_ratio
  - small ratio → under_distilled=False                  → test_balanced_not_under_distilled
  - ratio uses EXACT distilled fields (not all fields)   → test_distillation_ratio_excludes_raw
  - distilled=0 → ratio is None (no ZeroDivision)        → test_zero_distilled_ratio_is_none
  - empty input → all empty sets, ratio None             → test_empty_input_all_empty
  - live-data snapshot: 278741:28 ≈ 9955:1 → under_distilled → test_live_data_snapshot
"""

from __future__ import annotations

from cohezion.compound.memory_utilization import memory_utilization

# ---------------------------------------------------------------------------
# Layer status: dormant / sparse / healthy
# ---------------------------------------------------------------------------

_FLOOR = 50
_THRESHOLD = 100.0


def test_zero_count_is_dormant() -> None:
    """count=0 → dormant, NOT sparse or healthy.

    Kills an impl that uses `count < floor` for dormant (which would catch non-zero
    sparse counts too, blurring the boundary).
    """
    report = memory_utilization({"neuron": 0}, floor=_FLOOR, under_distilled_threshold=_THRESHOLD)
    assert "neuron" in report.dormant, "zero-count layer must be dormant"
    assert "neuron" not in report.sparse, "zero-count layer must NOT be sparse"
    assert "neuron" not in report.healthy, "zero-count layer must NOT be healthy"


def test_below_floor_is_sparse() -> None:
    """0 < count < floor → sparse (not dormant, not healthy).

    Kills an impl that maps all low counts to dormant.
    """
    report = memory_utilization(
        {"learnings": 10}, floor=_FLOOR, under_distilled_threshold=_THRESHOLD
    )
    assert "learnings" in report.sparse, "count=10 < floor=50 must be sparse"
    assert "learnings" not in report.dormant
    assert "learnings" not in report.healthy


def test_above_floor_is_healthy() -> None:
    """count >= floor → healthy (not dormant, not sparse).

    Kills an impl that marks all layers sparse regardless of count.
    """
    report = memory_utilization(
        {"journey_point": 278741}, floor=_FLOOR, under_distilled_threshold=_THRESHOLD
    )
    assert "journey_point" in report.healthy
    assert "journey_point" not in report.dormant
    assert "journey_point" not in report.sparse


def test_floor_boundary_is_healthy() -> None:
    """count == floor → healthy (boundary is inclusive-at-floor).

    Kills an impl that uses strict '<' at the floor boundary.
    """
    report = memory_utilization({"vault_notes": 50}, floor=50, under_distilled_threshold=_THRESHOLD)
    assert "vault_notes" in report.healthy


def test_dormant_not_in_sparse() -> None:
    """dormant and sparse are DISJOINT — a layer cannot be in both.

    Kills an impl that adds zero-count layers to both sets.
    """
    report = memory_utilization(
        {"mem0": 0, "neuron": 5},
        floor=_FLOOR,
        under_distilled_threshold=_THRESHOLD,
    )
    assert report.dormant.isdisjoint(report.sparse), (
        f"dormant and sparse must be disjoint; got dormant={report.dormant} sparse={report.sparse}"
    )
    assert report.dormant.isdisjoint(report.healthy)
    assert report.sparse.isdisjoint(report.healthy)


# ---------------------------------------------------------------------------
# Distillation ratio
# ---------------------------------------------------------------------------


def test_distillation_ratio_correct() -> None:
    """ratio = journey_point / sum(neuron + learnings + compound_learnings + mem0).

    Kills an impl that sums ALL counts or uses the wrong set of distilled layers.
    """
    counts = {
        "journey_point": 100,
        "neuron": 2,
        "learnings": 2,
        "compound_learnings": 2,
        "mem0": 2,
        "vault_notes": 1000,  # NOT a distilled layer — must be excluded from denominator
    }
    report = memory_utilization(counts, floor=_FLOOR, under_distilled_threshold=_THRESHOLD)
    # ratio = 100 / (2+2+2+2) = 100/8 = 12.5
    assert report.distillation_ratio is not None
    assert abs(report.distillation_ratio - 12.5) < 0.01, (
        f"ratio must be 100/8=12.5, got {report.distillation_ratio}"
    )


def test_distillation_ratio_excludes_raw() -> None:
    """vault_notes is NOT a distilled layer — its count must not appear in the denominator.

    Kills an impl that treats all non-journey_point layers as distilled.
    """
    # If vault_notes is wrongly included: ratio = 100 / (1 + 99) = 1.0 (wrong)
    # If excluded correctly:            ratio = 100 / 1           = 100.0
    counts = {"journey_point": 100, "mem0": 1, "vault_notes": 99}
    report = memory_utilization(counts, floor=_FLOOR, under_distilled_threshold=_THRESHOLD)
    assert report.distillation_ratio is not None
    assert abs(report.distillation_ratio - 100.0) < 0.01, (
        f"vault_notes must NOT be a distilled layer; ratio must be 100/1=100.0, "
        f"got {report.distillation_ratio}"
    )


def test_zero_distilled_ratio_is_none() -> None:
    """All distilled layers absent or zero → ratio is None (no ZeroDivisionError).

    Kills an impl that blindly divides raw / distilled without guarding zero.
    """
    report = memory_utilization(
        {"journey_point": 1000, "vault_notes": 50},
        floor=_FLOOR,
        under_distilled_threshold=_THRESHOLD,
    )
    assert report.distillation_ratio is None, (
        "No distilled layers present → ratio must be None, not a ZeroDivisionError"
    )


# ---------------------------------------------------------------------------
# Under-distilled flag
# ---------------------------------------------------------------------------


def test_under_distilled_huge_ratio() -> None:
    """ratio >= threshold → under_distilled=True.

    Kills an impl that never sets under_distilled.
    """
    counts = {"journey_point": 10000, "neuron": 1}  # ratio = 10000
    report = memory_utilization(counts, floor=_FLOOR, under_distilled_threshold=100.0)
    assert report.under_distilled is True, (
        "ratio=10000 >= threshold=100 must set under_distilled=True"
    )


def test_balanced_not_under_distilled() -> None:
    """ratio < threshold → under_distilled=False.

    Kills an impl that always sets under_distilled=True.
    """
    counts = {
        "journey_point": 50,
        "neuron": 10,
        "learnings": 10,
        "compound_learnings": 10,
        "mem0": 10,
    }
    # ratio = 50/40 = 1.25 << 100
    report = memory_utilization(counts, floor=_FLOOR, under_distilled_threshold=100.0)
    assert report.under_distilled is False, (
        "ratio=1.25 << threshold=100 must NOT be under_distilled"
    )


def test_under_distilled_none_ratio_is_false() -> None:
    """ratio=None (no distilled layers) → under_distilled=False (not an error).

    Kills an impl that raises or sets True when ratio is None.
    """
    report = memory_utilization(
        {"journey_point": 999}, floor=_FLOOR, under_distilled_threshold=100.0
    )
    assert report.distillation_ratio is None
    assert report.under_distilled is False


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


def test_empty_input_all_empty() -> None:
    """Empty layer_counts → all sets empty, ratio None, under_distilled=False. No crash."""
    report = memory_utilization({}, floor=_FLOOR, under_distilled_threshold=_THRESHOLD)
    assert len(report.dormant) == 0
    assert len(report.sparse) == 0
    assert len(report.healthy) == 0
    assert report.distillation_ratio is None
    assert report.under_distilled is False


# ---------------------------------------------------------------------------
# Live-data snapshot (2026-06-06 verified)
# ---------------------------------------------------------------------------


def test_live_data_snapshot() -> None:
    """Live data: journey_point=278741, neuron=18, learnings=10 → under_distilled.

    MAIN DISCRIMINATOR: mirrors the real diagnostic finding (item 106 motivation).
    ratio ≈ 278741/28 ≈ 9955:1 >> threshold=100.
    neuron=18 and learnings=10 are below floor=50 → sparse.
    journey_point=278741 is above floor → healthy.
    """
    counts = {
        "journey_point": 278741,
        "neuron": 18,
        "learnings": 10,
        "compound_learnings": 0,
        "mem0": 0,
        "vault_notes": 150,
    }
    report = memory_utilization(counts, floor=50, under_distilled_threshold=100.0)

    assert "journey_point" in report.healthy, "278741 >> floor=50 → healthy"
    assert "neuron" in report.sparse, "neuron=18 < floor=50 → sparse"
    assert "learnings" in report.sparse, "learnings=10 < floor=50 → sparse"
    assert "compound_learnings" in report.dormant, "compound_learnings=0 → dormant"
    assert "mem0" in report.dormant, "mem0=0 → dormant"

    assert report.distillation_ratio is not None
    # distilled = 18 + 10 + 0 + 0 = 28; ratio = 278741/28 ≈ 9955
    assert report.distillation_ratio > 9000, (
        f"ratio must be ~9955:1, got {report.distillation_ratio}"
    )
    assert report.under_distilled is True, "~9955:1 >> threshold=100 must set under_distilled=True"
