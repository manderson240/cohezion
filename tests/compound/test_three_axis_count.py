"""Item 473: three_axis_count() -- full 3-axis intersection count (2026-06-08).

``three_axis_count(problems, problem_class, finding_id, severity) -> int``:
Returns count of records matching ALL THREE of problem_class, finding_id, AND severity.
0 for absent triple.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: all three filters active.
     ClassA/fid_a/HIGH x2, ClassA/fid_a/LOW x1.
     three_axis_count(ClassA, fid_a, HIGH) = 2 (not 3 which is ClassA/fid_a total).
     Kills impl reusing problem_count_for_class_fid_pair (ignores severity).
  2. Severity-axis isolation: same class/fid, different severities -> different counts.
     Kills impl ignoring severity filter.
  3. Absent severity -> 0 (not raise).
     Kills impl without severity guard.
  4. Absent fid -> 0 (not raise).
     Kills impl without fid guard.
  5. Returns int not float.
     Distinguishes from ratio/proportion functions.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    three_axis_count,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_all_three_filters_active() -> None:
    """PRIMARY DISC.: counts records matching ALL THREE axes.

    ClassA/fid_a: HIGH x2, LOW x1.  Total ClassA/fid_a = 3.
    three_axis_count(ClassA, fid_a, HIGH) = 2, not 3.
    Kills impl reusing problem_count_for_class_fid_pair which returns 3.
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "LOW"),
        _p("ClassA", "fid_b", "HIGH"),
        _p("ClassB", "fid_a", "HIGH"),
    ]
    result = three_axis_count(problems, "ClassA", "fid_a", "HIGH")
    assert type(result) is int, "Must return int; got " + repr(type(result))
    assert result == 2, "ClassA/fid_a/HIGH=2; got " + repr(result)


def test_severity_axis_isolation() -> None:
    """Same class/fid, different severity -> different count.

    ClassA/fid_a: HIGH x3, LOW x1.  HIGH=3, LOW=1 (not 4 total).
    Kills impl ignoring severity filter.
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "LOW"),
    ]
    high_result = three_axis_count(problems, "ClassA", "fid_a", "HIGH")
    low_result = three_axis_count(problems, "ClassA", "fid_a", "LOW")
    assert high_result == 3, "HIGH=3; got " + repr(high_result)
    assert low_result == 1, "LOW=1; got " + repr(low_result)


def test_absent_severity_returns_zero() -> None:
    """Absent severity -> 0 (not raise)."""
    problems = [_p("ClassA", "fid_a", "HIGH")]
    result = three_axis_count(problems, "ClassA", "fid_a", "NONEXISTENT")
    assert result == 0, "Absent severity -> 0; got " + repr(result)


def test_absent_fid_returns_zero() -> None:
    """Absent fid -> 0 (not raise)."""
    problems = [_p("ClassA", "fid_a", "HIGH")]
    result = three_axis_count(problems, "ClassA", "NONEXISTENT", "HIGH")
    assert result == 0, "Absent fid -> 0; got " + repr(result)


def test_returns_int_not_float() -> None:
    """Returns int, not float."""
    problems = [_p("ClassA", "fid_a", "HIGH"), _p("ClassA", "fid_a", "HIGH")]
    result = three_axis_count(problems, "ClassA", "fid_a", "HIGH")
    assert type(result) is int, "Must be int; got " + repr(type(result))
    assert result == 2, "Two matches -> 2; got " + repr(result)
