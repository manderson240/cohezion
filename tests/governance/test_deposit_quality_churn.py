"""Item 128: deposit_quality_churn — TDD red→green (2026-06-08).

``deposit_quality_churn(before, after)`` returns the name-level delta across
two ``DepositQualityReport``s — WHICH neurons entered/left each problem set, not
just how many (item-74's count-level delta).

Per problem-class (redundant, low_evidence, format_invalid):
  - ``newly``: names in ``after`` but NOT ``before`` (new problem since last scan)
  - ``resolved``: names in ``before`` but NOT ``after`` (fixed since last scan)
  - a name in BOTH → in NEITHER list

Discriminating tests — each kills a plausible wrong implementation:

  1. before-only → resolved; after-only → newly  (PRIMARY DISC.: kills "newly=after names")
  2. Common name → neither list                  (kills "resolved=before names")
  3. Identical reports → all-empty               (kills impl reporting shared names)
  4. Empty reports → all-empty (no crash)        (kills impl that raises)
  5. Three classes tracked independently         (kills impl merging all classes)
"""

from __future__ import annotations

from cohezion.governance.neuron_quality import DepositQualityReport
from cohezion.governance.quality_churn import deposit_quality_churn


def _report(
    redundant: dict[str, int] | None = None,
    low_evidence: list[str] | None = None,
    format_invalid: list[str] | None = None,
) -> DepositQualityReport:
    return DepositQualityReport(
        redundant=redundant or {},
        low_evidence=low_evidence or [],
        format_invalid=format_invalid or [],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_before_only_resolved_after_only_newly() -> None:
    """A name in before.low_evidence but not after → resolved; in after but not before → newly.

    PRIMARY DISCRIMINATOR: kills an impl that sets newly = set(after.low_evidence),
    which would include names common to both.
    """
    before = _report(low_evidence=["alice", "bob"])
    after = _report(low_evidence=["bob", "charlie"])
    churn = deposit_quality_churn(before, after)
    assert "alice" in churn.low_evidence.resolved, (
        f"alice (before-only) must be resolved; got {churn.low_evidence}"
    )
    assert "charlie" in churn.low_evidence.newly, (
        f"charlie (after-only) must be newly; got {churn.low_evidence}"
    )


def test_common_name_in_neither_list() -> None:
    """A name in BOTH before and after → in neither resolved nor newly.

    Kills an impl that reports every name in before as resolved.
    """
    before = _report(format_invalid=["alpha", "beta"])
    after = _report(format_invalid=["beta", "gamma"])
    churn = deposit_quality_churn(before, after)
    assert "beta" not in churn.format_invalid.resolved, (
        f"beta (in both) must NOT be resolved; got {churn.format_invalid}"
    )
    assert "beta" not in churn.format_invalid.newly, (
        f"beta (in both) must NOT be newly; got {churn.format_invalid}"
    )


def test_identical_reports_all_empty() -> None:
    """Identical before and after → all three classes empty.

    Kills an impl that re-reports common names.
    """
    report = _report(
        redundant={"x": 2, "y": 3},
        low_evidence=["a", "b"],
        format_invalid=["c"],
    )
    churn = deposit_quality_churn(report, report)
    assert churn.redundant.resolved == []
    assert churn.redundant.newly == []
    assert churn.low_evidence.resolved == []
    assert churn.low_evidence.newly == []
    assert churn.format_invalid.resolved == []
    assert churn.format_invalid.newly == []


def test_empty_reports_all_empty() -> None:
    """Both empty reports → all lists empty (no crash)."""
    churn = deposit_quality_churn(_report(), _report())
    assert churn.redundant.resolved == []
    assert churn.redundant.newly == []
    assert churn.low_evidence.resolved == []
    assert churn.low_evidence.newly == []
    assert churn.format_invalid.resolved == []
    assert churn.format_invalid.newly == []


def test_three_classes_tracked_independently() -> None:
    """Changes in each problem class are tracked independently.

    Kills an impl that merges all three classes into a single pool.
    'alice' in low_evidence must not contaminate the format_invalid result.
    """
    before = _report(low_evidence=["alice"], format_invalid=["bob"])
    after = _report(low_evidence=[], format_invalid=["bob", "carol"])
    churn = deposit_quality_churn(before, after)
    # low_evidence: alice resolved, carol NOT in low_evidence (only in format_invalid after)
    assert "alice" in churn.low_evidence.resolved, (
        f"alice must be low_evidence.resolved; got {churn.low_evidence}"
    )
    assert "carol" not in churn.low_evidence.newly, (
        f"carol must NOT appear in low_evidence.newly; got {churn.low_evidence}"
    )
    # format_invalid: bob in both (neither), carol newly
    assert "carol" in churn.format_invalid.newly, (
        f"carol must be format_invalid.newly; got {churn.format_invalid}"
    )
    assert "bob" not in churn.format_invalid.resolved, (
        f"bob (in both) must NOT be format_invalid.resolved; got {churn.format_invalid}"
    )
