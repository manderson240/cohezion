"""Discriminating tests for deposit_quality_churn (backlog item 128, 2026-06-08).

`deposit_quality_churn(before, after)` is the name-level dual of item-74's count-level
`deposit_quality_delta`: per problem class (redundant / low_evidence / format_invalid) it reports
`newly` (names in after not before — fix THIS) and `resolved` (names in before not after — a fix
that landed), compared by NAME. Report-only, pure over two injected DepositQualityReports.

Each test fails a plausible wrong impl:
  - an impl that lists every COMMON name → test_name_in_both_in_neither,
  - an impl comparing redundant by (name,count) not name → test_redundant_count_change_is_not_churn,
  - an impl that swaps newly/resolved → test_newly_and_resolved_directions,
  - an impl that miscompares identical snapshots → test_identical_all_empty.
"""

from __future__ import annotations

from cohezion.governance.neuron_quality import (
    DepositQualityReport,
    deposit_quality_churn,
)


def _report(*, redundant=None, low_evidence=None, format_invalid=None) -> DepositQualityReport:
    return DepositQualityReport(
        redundant=redundant or {},
        low_evidence=low_evidence or [],
        format_invalid=format_invalid or [],
    )


def test_newly_and_resolved_directions() -> None:
    before = _report(low_evidence=["a"], format_invalid=["x"])
    after = _report(low_evidence=[], format_invalid=["x", "y"])
    churn = deposit_quality_churn(before, after)
    assert churn.low_evidence.resolved == ["a"]  # 'a' left the low_evidence set → a fix landed
    assert churn.low_evidence.newly == []
    assert churn.format_invalid.newly == ["y"]  # 'y' just became format-invalid → fix THIS
    assert churn.format_invalid.resolved == []


def test_name_in_both_in_neither() -> None:
    # DISCRIMINATING: a name present in BOTH snapshots is unchanged churn — in NEITHER list. An impl
    # that lists every common name would wrongly include it.
    before = _report(low_evidence=["a", "b"])
    after = _report(low_evidence=["a", "c"])
    churn = deposit_quality_churn(before, after)
    assert "a" not in churn.low_evidence.newly and "a" not in churn.low_evidence.resolved
    assert churn.low_evidence.newly == ["c"]
    assert churn.low_evidence.resolved == ["b"]


def test_redundant_count_change_is_not_churn() -> None:
    # DISCRIMINATING: redundant is a dict; churn is by NAME (key), not (name,count). A neuron whose
    # redundancy count changed but is still redundant is in NEITHER list. An impl comparing
    # (name,count) pairs would mark it both newly and resolved.
    before = _report(redundant={"dup": 2})
    after = _report(redundant={"dup": 5})
    churn = deposit_quality_churn(before, after)
    assert churn.redundant.newly == []
    assert churn.redundant.resolved == []


def test_redundant_key_churn() -> None:
    before = _report(redundant={"old": 2})
    after = _report(redundant={"new": 3})
    churn = deposit_quality_churn(before, after)
    assert churn.redundant.newly == ["new"]
    assert churn.redundant.resolved == ["old"]


def test_identical_all_empty() -> None:
    rep = _report(redundant={"d": 2}, low_evidence=["a"], format_invalid=["x"])
    churn = deposit_quality_churn(rep, rep)
    for pc in (churn.redundant, churn.low_evidence, churn.format_invalid):
        assert pc.newly == [] and pc.resolved == []


def test_results_sorted() -> None:
    before = _report(format_invalid=[])
    after = _report(format_invalid=["z", "a", "m"])
    churn = deposit_quality_churn(before, after)
    assert churn.format_invalid.newly == ["a", "m", "z"]  # sorted, deterministic
