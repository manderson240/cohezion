"""Item 442: class_count_for_severity() -- distinct class count for a severity (2026-06-08).

``class_count_for_severity(problems, severity) -> int``:
Returns the number of DISTINCT problem_class values that have at least one
Problem with the given severity.  0 for unknown/empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts DISTINCT classes (not total records).
     Kills impl returning len(problems_for_severity(...)).
  2. One class with many problems of given severity still counts as 1.
     Validates the distinct-not-count semantic.
  3. Unknown severity -> 0 (not raise).
     Kills impl that errors on missing key.
  4. Empty -> 0 (not raise).
     Kills impl with unguarded access.
  5. Returns int (not set or list).
     Validates the structural type of the return value.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_count_for_severity,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_counts_distinct_classes_not_records() -> None:
    """PRIMARY DISC.: distinct classes, not total records.

    One class 'BUG' appears 3 times with 'HIGH' severity -> count=1 not 3.
    Kills impl returning len(problems_for_severity(...)).
    """
    problems = [
        _p("BUG", "f1", "HIGH"),
        _p("BUG", "f2", "HIGH"),
        _p("BUG", "f3", "HIGH"),
        _p("PERF", "f4", "LOW"),
    ]
    result = class_count_for_severity(problems, "HIGH")
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 1, "One distinct class ('BUG') has HIGH; got " + repr(result)


def test_one_class_many_records_still_counts_as_one() -> None:
    """Single class with multiple HIGH records -> 1 (distinct count)."""
    problems = [
        _p("ONLY", "f1", "CRITICAL"),
        _p("ONLY", "f2", "CRITICAL"),
        _p("ONLY", "f3", "CRITICAL"),
    ]
    result = class_count_for_severity(problems, "CRITICAL")
    assert result == 1, "One class with 3 records = 1 distinct class; got " + repr(result)


def test_unknown_severity_returns_zero() -> None:
    """Unknown severity -> 0, not raise."""
    problems = [_p("cls", "f1", "HIGH")]
    result = class_count_for_severity(problems, "NONEXISTENT")
    assert result == 0, "Unknown severity -> 0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0, not raise."""
    result = class_count_for_severity([], "HIGH")
    assert result == 0, "Empty -> 0; got " + repr(result)
    assert isinstance(result, int)


def test_multiple_classes_correct_count() -> None:
    """Multiple distinct classes with given severity -> correct count."""
    problems = [
        _p("BUG", "f1", "HIGH"),
        _p("PERF", "f2", "HIGH"),
        _p("SEC", "f3", "HIGH"),
        _p("SEC", "f4", "HIGH"),  # duplicate class for HIGH
        _p("OTHER", "f5", "LOW"),
    ]
    result = class_count_for_severity(problems, "HIGH")
    assert result == 3, "BUG, PERF, SEC = 3 distinct classes; got " + repr(result)
