"""Item 120: trace_compaction_ratio — TDD red→green (2026-06-08).

``trace_compaction_ratio(records)`` measures storage-density evolution in the
recursive trace store — the "floppy-disk compaction analogy":

  high ratio  = many raw task→strategy records collapse into FEW distinct
                strategies → good densification (loop is LEARNING)
  ratio ≈ 1.0 = every raw record is a unique strategy → no densification
                (loop is merely ACCUMULATING, like an un-evolved floppy)

Input: list of (failure_class, strategy) pairs.
Output: CompactionReport(n_records, n_distinct_strategies, compaction_ratio).

Discriminating tests — each kills a plausible wrong implementation:

  1. 6 tasks → 2 distinct strategies → ratio == 3.0       (MAIN DISC.: kills "ratio=n_distinct/n_records")
  2. Every task unique → ratio == 1.0                     (kills "always report densification")
  3. Empty records → {0, 0, 0.0}                          (kills an impl that raises ZeroDivision)
  4. All same strategy → ratio == n_records               (extreme densification; kills "cap at 3.0")
  5. Ratio formula: n_records / n_distinct                (kills "n_distinct / n_records" inversion)
  6. n_records and n_distinct are exact counts             (kills "count unique failure_classes instead")
"""

from __future__ import annotations

from cohezion.recursive_trace.compaction import trace_compaction_ratio


def test_densified_ratio_3() -> None:
    """6 records → 2 distinct strategies → compaction_ratio == 3.0.

    PRIMARY DISCRIMINATOR: kills an impl that returns 2/6 (= 0.33) by inverting
    the formula, OR one that always returns 1.0.
    """
    records = [
        ("latency", "tier_downgrade"),
        ("latency", "tier_downgrade"),
        ("latency", "tier_downgrade"),
        ("context_overflow", "summarise_first"),
        ("context_overflow", "summarise_first"),
        ("context_overflow", "summarise_first"),
    ]
    report = trace_compaction_ratio(records)
    assert report.compaction_ratio == 3.0, (
        f"6 records / 2 strategies must → ratio 3.0; got {report.compaction_ratio}"
    )


def test_no_densification_ratio_1() -> None:
    """Every record has a unique strategy → ratio == 1.0 (no densification).

    Kills an impl that always reports densification (ratio > 1).
    """
    records = [
        ("err_a", "strategy_alpha"),
        ("err_b", "strategy_beta"),
        ("err_c", "strategy_gamma"),
    ]
    report = trace_compaction_ratio(records)
    assert report.compaction_ratio == 1.0, (
        f"all-unique strategies must → ratio 1.0; got {report.compaction_ratio}"
    )


def test_empty_records_zero() -> None:
    """Empty list → CompactionReport(0, 0, 0.0) — no ZeroDivisionError.

    Kills an impl that raises on empty input or returns ratio 1.0.
    """
    report = trace_compaction_ratio([])
    assert report.n_records == 0
    assert report.n_distinct_strategies == 0
    assert report.compaction_ratio == 0.0, (
        f"empty records must → ratio 0.0; got {report.compaction_ratio}"
    )


def test_all_same_strategy_max_ratio() -> None:
    """All 4 records share the same strategy → ratio == 4.0 (extreme densification).

    Kills an impl that caps the ratio at some fixed maximum.
    """
    records = [
        ("type_a", "golden_strategy"),
        ("type_b", "golden_strategy"),
        ("type_c", "golden_strategy"),
        ("type_d", "golden_strategy"),
    ]
    report = trace_compaction_ratio(records)
    assert report.compaction_ratio == 4.0, (
        f"4 records / 1 strategy must → ratio 4.0; got {report.compaction_ratio}"
    )


def test_formula_is_records_over_distinct() -> None:
    """Ratio is n_records / n_distinct_strategies (not the inverse).

    Kills an impl that computes n_distinct / n_records (which would give < 1
    for any densification).
    """
    records = [
        ("x", "s1"),
        ("y", "s1"),
        ("z", "s2"),
    ]
    report = trace_compaction_ratio(records)
    # 3 records, 2 distinct → ratio = 3/2 = 1.5
    assert report.compaction_ratio == 1.5, f"3/2 = 1.5; got {report.compaction_ratio}"


def test_counts_are_exact() -> None:
    """n_records and n_distinct_strategies report the exact counts.

    Kills an impl that counts unique failure_classes instead of unique strategies.
    All 3 records have DIFFERENT failure_classes but only 1 distinct strategy.
    """
    records = [
        ("class_a", "shared_strategy"),
        ("class_b", "shared_strategy"),
        ("class_c", "shared_strategy"),
    ]
    report = trace_compaction_ratio(records)
    assert report.n_records == 3, f"must count all records; got {report.n_records}"
    assert report.n_distinct_strategies == 1, (
        f"1 distinct strategy; got {report.n_distinct_strategies}"
    )
