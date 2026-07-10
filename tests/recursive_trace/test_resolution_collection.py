"""Discriminating tests for the failure-resolution collection + coupling analysis.

Design: docs/research/FAILURE_RESOLUTION_COLLECTION_DESIGN_2026-06-05.md

The analysis is the scientific core: it must return KEEP on data where the failure-class
predicts the resolver, and RETIRE on data where it does NOT. The most plausible WRONG
analysis is one that conflates "a strategy resolves things" with "the failure-class
predicts which strategy" — i.e. an impl that fires KEEP even on independent data. The
independence test below fails exactly that wrong impl.
"""

from __future__ import annotations

from cohezion.recursive_trace.coupling_analysis import (
    analyze_domain,
    coupling_delta,
    permutation_pvalue,
)
from cohezion.recursive_trace.resolution_log import read_resolutions, record_resolution


# ---- collection primitive -------------------------------------------------------


def test_record_and_read_roundtrip(tmp_path) -> None:
    p = tmp_path / "res.jsonl"
    record_resolution("quality_gate", "code", "cpu", True, path=p, task_hash="h1")
    record_resolution("quality_gate", "short_answer", "npu", True, path=p)
    rows = read_resolutions(path=p)
    assert len(rows) == 2
    assert rows[0]["domain"] == "quality_gate" and rows[0]["strategy"] == "cpu"
    assert rows[0]["task_hash"] == "h1" and rows[0]["success"] is True


def test_domain_filter_and_successful_only(tmp_path) -> None:
    p = tmp_path / "res.jsonl"
    record_resolution("quality_gate", "code", "cpu", True, path=p)
    record_resolution("routing", "duration", "igpu", False, path=p)
    assert len(read_resolutions("quality_gate", path=p)) == 1
    assert read_resolutions(successful_only=True, path=p)[0]["domain"] == "quality_gate"


def test_unknown_domain_rejected(tmp_path) -> None:
    # Discriminates a coercing impl: a typo'd domain must raise, not silently mis-bucket.
    p = tmp_path / "res.jsonl"
    try:
        record_resolution("qualtiy_gate", "code", "cpu", True, path=p)
        raise AssertionError("expected ValueError on unknown domain")
    except ValueError:
        pass


# ---- coupling analysis (the part that can return RETIRE) -------------------------


def _dependent_pairs() -> list[tuple[str, str]]:
    # fc perfectly predicts rs, but the two strategies are EQUALLY common globally
    # (so marginal ordering is a coin-flip while conditional ordering is certain).
    pairs = []
    for _ in range(40):
        pairs.append(("A", "X"))
        pairs.append(("B", "Y"))
    return pairs


def _independent_pairs() -> list[tuple[str, str]]:
    # Same strategy mix within EVERY failure-class -> knowing fc tells you nothing.
    pairs = []
    for fc in ("A", "B", "C"):
        for _ in range(20):
            pairs.append((fc, "X"))
            pairs.append((fc, "Y"))
    return pairs


def test_dependent_data_yields_positive_delta() -> None:
    # Conditional ordering reaches the resolver in 1 attempt; marginal averages 1.5.
    d = coupling_delta(_dependent_pairs())
    assert d > 0.4  # ~0.5 attempts saved


def test_independent_data_yields_near_zero_delta() -> None:
    # Discriminating: with fc ⊥ rs the conditional policy has NO edge -> Δ ≈ 0.
    d = coupling_delta(_independent_pairs())
    assert abs(d) < 0.05


def test_analyze_keep_on_dependent_data() -> None:
    res = analyze_domain(_dependent_pairs(), n_min=60, k_min=2, n_perm=500)
    assert res["verdict"] == "KEEP"
    assert res["p_value"] < 0.05


def test_analyze_retire_on_independent_data() -> None:
    # THE discriminating case: a wrong analysis that only checks "do strategies resolve"
    # would KEEP here. The permutation null must place Δ inside chance -> RETIRE.
    res = analyze_domain(_independent_pairs(), n_min=60, k_min=2, n_perm=500)
    assert res["verdict"] == "RETIRE"


def test_analyze_unproven_below_volume_floor() -> None:
    small = [("A", "X"), ("B", "Y"), ("A", "X")]
    res = analyze_domain(small, n_min=60, k_min=3)
    assert res["verdict"] == "UNPROVEN"


def test_permutation_pvalue_high_for_independent() -> None:
    _, p = permutation_pvalue(_independent_pairs(), n_perm=500)
    assert p > 0.05
