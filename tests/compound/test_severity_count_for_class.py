"""Item 469: severity_count_for_class() -- cross-axis intersection count (2026-06-08).

``severity_count_for_class(problems, problem_class, severity) -> int``:
Returns count of records matching BOTH problem_class AND severity.
0 for absent pair.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts only records matching BOTH class AND severity.
     ClassA: HIGH x 3, LOW x 2.  ClassB: HIGH x 5.
     severity_count_for_class(ClassA, HIGH) = 3 (not 5 which is ClassB HIGH).
     Kills impl reusing class_histogram()[cls] (ignores severity filter).
  2. Absent class -> 0 (not raise).
     Kills impl without class guard.
  3. Absent severity -> 0 (not raise).
     Kills impl without severity guard.
  4. Result <= class total count (at most all class records have that severity).
     Validates intersection semantics.
  5. Returns int (not float, not bool).
     Distinguishes from severity_labelling_ratio (float).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_count_for_class,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_counts_both_class_and_severity() -> None:
    """PRIMARY DISC.: counts records matching BOTH class AND severity.

    ClassA: HIGH x3, LOW x2.  ClassB: HIGH x5.
    severity_count_for_class(ClassA, HIGH) = 3.
    Not 5 (ClassB HIGH) -- kills impl not filtering by class.
    Not 5 (ClassA total) -- kills impl not filtering by severity.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassA", "f3", "HIGH"),
        _p("ClassA", "f4", "LOW"),
        _p("ClassA", "f5", "LOW"),
        _p("ClassB", "f6", "HIGH"),
        _p("ClassB", "f7", "HIGH"),
        _p("ClassB", "f8", "HIGH"),
        _p("ClassB", "f9", "HIGH"),
        _p("ClassB", "f10", "HIGH"),
    ]
    result = severity_count_for_class(problems, "ClassA", "HIGH")
    assert type(result) is int, "Must return int; got " + repr(type(result))
    assert result == 3, "ClassA HIGH count=3; got " + repr(result)


def test_absent_class_returns_zero() -> None:
    """Absent class -> 0 (not raise)."""
    problems = [_p("ClassA", "f1", "HIGH")]
    result = severity_count_for_class(problems, "NONEXISTENT", "HIGH")
    assert result == 0, "Absent class -> 0; got " + repr(result)


def test_absent_severity_returns_zero() -> None:
    """Absent severity -> 0 (not raise)."""
    problems = [_p("ClassA", "f1", "HIGH")]
    result = severity_count_for_class(problems, "ClassA", "NONEXISTENT")
    assert result == 0, "Absent severity -> 0; got " + repr(result)


def test_count_leq_class_total() -> None:
    """Intersection count <= total class count (subset semantics)."""
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassA", "f3", "LOW"),
    ]
    # ClassA total = 3, ClassA+HIGH = 2
    result = severity_count_for_class(problems, "ClassA", "HIGH")
    assert result == 2, "ClassA HIGH=2; got " + repr(result)
    assert result <= 3, "count must be <= class total 3; got " + repr(result)


def test_returns_int_not_float_or_bool() -> None:
    """Returns int, not float or bool."""
    problems = [_p("c", "f1", "HIGH")]
    result = severity_count_for_class(problems, "c", "HIGH")
    assert type(result) is int, "Must be int; got " + repr(type(result))
    assert result == 1, "Single match -> 1; got " + repr(result)
