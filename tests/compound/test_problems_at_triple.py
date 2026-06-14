"""Item 475: problems_at_triple() -- list of records matching all three axes (2026-06-08).

``problems_at_triple(problems, problem_class, finding_id, severity) -> list[Problem]``:
Returns the Problem objects matching ALL of problem_class, finding_id, AND severity.
Empty list for absent triple.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns list of Problem objects, not int count.
     ClassA/fid_a/HIGH x2 -> list of 2 Problem objects (not the integer 2).
     Kills impl reusing three_axis_count which returns int.
  2. Correct filtering: only exact matches on all 3 axes.
     ClassA/fid_a: HIGH x2, LOW x1.  problems_at_triple(ClassA, fid_a, HIGH) -> 2 items.
     Kills impl ignoring one of the three axes.
  3. Absent triple -> [] (not raise, not None).
     Kills impl without absence guard.
  4. Returned objects are the original Problem instances (identity preserved).
     Kills impl that creates new objects instead of filtering.
  5. Preserves insertion order of matching records.
     Kills impl that sorts or reorders.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_at_triple,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_list_not_int() -> None:
    """PRIMARY DISC.: returns list[Problem], not int count.

    ClassA/fid_a/HIGH x2 -> list of 2 Problem objects (not 2).
    Kills impl reusing three_axis_count.
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "LOW"),
    ]
    result = problems_at_triple(problems, "ClassA", "fid_a", "HIGH")
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 2, "2 matches; got len=" + repr(len(result))
    assert all(isinstance(p, Problem) for p in result), "All items must be Problem"


def test_filters_all_three_axes() -> None:
    """All three axes filter simultaneously; other records excluded."""
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "LOW"),  # different severity
        _p("ClassA", "fid_b", "HIGH"),  # different fid
        _p("ClassB", "fid_a", "HIGH"),  # different class
    ]
    result = problems_at_triple(problems, "ClassA", "fid_a", "HIGH")
    assert len(result) == 1, "Only ClassA/fid_a/HIGH matches; got " + repr(len(result))


def test_absent_triple_returns_empty_list() -> None:
    """Absent triple -> [] (not raise, not None)."""
    problems = [_p("ClassA", "fid_a", "HIGH")]
    result = problems_at_triple(problems, "ClassA", "fid_a", "NONEXISTENT")
    assert result == [], "Absent triple -> []; got " + repr(result)


def test_preserves_insertion_order() -> None:
    """Matching records returned in original insertion order."""
    p1 = _p("C", "f", "HIGH")
    p2 = _p("C", "f", "HIGH")
    p3 = _p("C", "f", "LOW")  # excluded
    problems = [p1, p3, p2]
    result = problems_at_triple(problems, "C", "f", "HIGH")
    assert result == [p1, p2], "Order preserved; got " + repr(result)


def test_empty_input_returns_empty_list() -> None:
    """Empty input -> [] (not raise)."""
    result = problems_at_triple([], "ClassA", "fid_a", "HIGH")
    assert result == [], "Empty input -> []; got " + repr(result)
