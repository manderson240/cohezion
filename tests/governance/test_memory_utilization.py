"""Discriminating tests for memory_utilization (backlog item 106, 2026-06-08).

`memory_utilization(layer_counts, *, sparse_floor, under_distilled_ratio)` answers the user's
2026-06-06 diagnostic "are we leveraging all our memory?" — it classifies each memory layer
(dormant/sparse/healthy) and computes the raw:distilled distillation ratio (raw = journey_point;
distilled = neuron+learnings+compound_learnings+mem0). Report-only, pure over injected counts.

Each test fails a plausible wrong impl:
  - an impl that does raw/distilled without a guard CRASHES → test_no_distilled_no_zerodivision,
  - an impl that only counts `neuron` as distilled → test_distilled_sums_all_four,
  - an impl that divides by fired/known layers instead of classifying each → test_layer_status,
  - an impl that flags balanced stores → test_balanced_not_under_distilled.
"""

from __future__ import annotations

from cohezion.governance.neuron_quality import MemoryUtilization, memory_utilization


def test_empty_input_all_empty() -> None:
    out = memory_utilization({})
    assert isinstance(out, MemoryUtilization)
    assert out.layer_status == {}
    assert out.raw_count == 0 and out.distilled_count == 0
    assert out.distillation_ratio is None
    assert out.under_distilled is False


def test_layer_status() -> None:
    out = memory_utilization(
        {"journey_point": 5000, "neuron": 0, "learnings": 10}, sparse_floor=100
    )
    assert out.layer_status["journey_point"] == "healthy"  # >= floor
    assert out.layer_status["neuron"] == "dormant"  # count == 0
    assert out.layer_status["learnings"] == "sparse"  # 0 < 10 < 100


def test_dormant_takes_precedence_over_sparse() -> None:
    # count == 0 is dormant, never sparse (dormant is the stronger signal).
    out = memory_utilization({"mem0": 0}, sparse_floor=100)
    assert out.layer_status["mem0"] == "dormant"


def test_floor_boundary_is_healthy() -> None:
    # exactly at the floor → healthy (sparse is strictly below).
    out = memory_utilization({"neuron": 100}, sparse_floor=100)
    assert out.layer_status["neuron"] == "healthy"


def test_under_distilled_huge_ratio() -> None:
    # The live 2026-06-06 bottleneck shape: ~15000:1 raw:distilled.
    out = memory_utilization(
        {"journey_point": 278741, "neuron": 18, "learnings": 10}, under_distilled_ratio=100.0
    )
    assert out.raw_count == 278741
    assert out.distilled_count == 28
    assert out.distillation_ratio == 278741 / 28
    assert out.under_distilled is True


def test_distilled_sums_all_four() -> None:
    # DISCRIMINATING: distilled = neuron+learnings+compound_learnings+mem0 (all four). An impl that
    # counts only `neuron` would compute distilled=1 → ratio=8.0, not 2.0.
    out = memory_utilization(
        {"journey_point": 8, "neuron": 1, "learnings": 1, "compound_learnings": 1, "mem0": 1},
        under_distilled_ratio=100.0,
    )
    assert out.distilled_count == 4
    assert out.distillation_ratio == 2.0
    assert out.under_distilled is False  # 2.0 is well below the threshold


def test_no_distilled_no_zerodivision() -> None:
    # DISCRIMINATING: raw > 0 with NO distilled layers must NOT ZeroDivisionError — it is the
    # maximal bottleneck: ratio None, under_distilled True.
    out = memory_utilization({"journey_point": 500})
    assert out.distilled_count == 0
    assert out.distillation_ratio is None
    assert out.under_distilled is True


def test_no_raw_not_under_distilled() -> None:
    # distilled records exist but no raw firehose → not a bottleneck (under_distilled False).
    out = memory_utilization({"neuron": 50, "learnings": 30})
    assert out.raw_count == 0
    assert out.under_distilled is False


def test_balanced_not_under_distilled() -> None:
    # DISCRIMINATING: a balanced store (ratio below threshold) is NOT flagged.
    out = memory_utilization(
        {"journey_point": 100, "neuron": 50, "learnings": 30, "compound_learnings": 20, "mem0": 10},
        sparse_floor=5,
        under_distilled_ratio=100.0,
    )
    assert all(s == "healthy" for s in out.layer_status.values())
    assert out.distillation_ratio == 100 / 110
    assert out.under_distilled is False
