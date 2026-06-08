"""Item 443: fid_count_for_severity() -- count distinct fids for a severity (2026-06-08).

``fid_count_for_severity(problems, severity) -> int``:
Returns the number of distinct finding_ids that have at least one Problem
with the given severity value.  0 for unknown or empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts DISTINCT finding_ids (not record count).
     One fid with multiple HIGH records still counts as 1.
     Kills impl returning len(problems_for_severity(...)).
  2. Result is int (not set or list).
     Kills impl returning the set itself.
  3. 0 for unknown severity (not raise).
     Kills impl that errors on missing severity.
  4. 0 for empty (not raise).
     Kills impl with unguarded access.
  5. Multiple distinct fids correctly counted.
     Validates counting logic against class field (kills impl using wrong field).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fid_count_for_severity,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_counts_distinct_fids_not_records() -> None:
    """PRIMARY DISC.: counts DISTINCT fids, not problem records.

    One fid 'f1' appears 3 times with HIGH severity -> count = 1.
    Kills impl returning 3 (record count).
    """
    problems = [
        _p("cls", "f1", "HIGH"),
        _p("cls", "f1", "HIGH"),
        _p("cls", "f1", "HIGH"),
        _p("cls", "f2", "LOW"),
    ]
    result = fid_count_for_severity(problems, "HIGH")
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 1, "f1 appears 3x but is 1 distinct fid; got " + repr(result)


def test_one_fid_many_records_still_counts_as_one() -> None:
    """One fid with many HIGH records -> count = 1 (distinct, not total)."""
    problems = [_p(f"c{i}", "f1", "HIGH") for i in range(5)]
    result = fid_count_for_severity(problems, "HIGH")
    assert result == 1, "All 5 records share fid='f1' -> count=1; got " + repr(result)


def test_unknown_severity_returns_zero() -> None:
    """Unknown severity -> 0 (not raise)."""
    problems = [_p("cls", "f1", "HIGH")]
    result = fid_count_for_severity(problems, "NONEXISTENT")
    assert result == 0, "Unknown severity -> 0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0, not raise."""
    result = fid_count_for_severity([], "HIGH")
    assert result == 0, "Empty -> 0; got " + repr(result)
    assert isinstance(result, int)


def test_multiple_distinct_fids_correct_count() -> None:
    """Multiple distinct fids with the same severity are all counted."""
    problems = [
        _p("a", "f1", "HIGH"),
        _p("b", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("d", "f4", "LOW"),
        _p("e", "f5", "LOW"),
    ]
    result_high = fid_count_for_severity(problems, "HIGH")
    result_low = fid_count_for_severity(problems, "LOW")
    assert result_high == 3, "3 distinct fids with HIGH; got " + repr(result_high)
    assert result_low == 2, "2 distinct fids with LOW; got " + repr(result_low)
