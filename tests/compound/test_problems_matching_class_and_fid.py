"""Item 481: problems_matching_class_and_fid() -- 2-axis filter (class x fid) (2026-06-08).

``problems_matching_class_and_fid(problems, problem_class, finding_id) -> list[Problem]``:
Returns Problem objects matching BOTH problem_class AND finding_id.
Empty list for absent pair.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns list of Problem objects, not int count.
     ClassA/fid_a x3 -> list of 3 Problem objects (not the integer 3).
     Kills impl reusing problem_count_for_class_fid_pair which returns int.
  2. Both axes filter simultaneously.
     ClassA: fid_a x3, fid_b x2.  query(ClassA, fid_a) -> 3 objects (not 5).
     Kills impl not filtering by fid.
  3. Cross-class isolation: ClassB/fid_a not included.
     Kills impl not filtering by class.
  4. Absent pair -> [] (not raise).
     Kills impl without absence guard.
  5. Preserves insertion order.
     Kills impl that sorts.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_matching_class_and_fid,
)


def _p(cls: str, fid: str, sev: str = "HIGH") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_list_not_count() -> None:
    """PRIMARY DISC.: returns list[Problem], not int.

    ClassA/fid_a x3 -> list of 3 Problem objects (not 3).
    Kills impl reusing problem_count_for_class_fid_pair.
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "LOW"),
        _p("ClassA", "fid_a", "MED"),
        _p("ClassA", "fid_b", "HIGH"),  # excluded
    ]
    result = problems_matching_class_and_fid(problems, "ClassA", "fid_a")
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 3, "ClassA/fid_a=3; got len=" + repr(len(result))
    assert all(isinstance(p, Problem) for p in result)
    assert all(p.problem_class == "ClassA" and p.finding_id == "fid_a" for p in result)


def test_both_axes_filter_simultaneously() -> None:
    """Both class AND fid filter; ClassA/fid_b excluded."""
    problems = [
        _p("ClassA", "fid_a"),
        _p("ClassA", "fid_a"),
        _p("ClassA", "fid_a"),
        _p("ClassA", "fid_b"),  # different fid
        _p("ClassA", "fid_b"),  # different fid
    ]
    result = problems_matching_class_and_fid(problems, "ClassA", "fid_a")
    assert len(result) == 3, "ClassA/fid_a=3; got " + repr(len(result))


def test_cross_class_isolation() -> None:
    """ClassB/fid_a not returned when querying ClassA/fid_a."""
    problems = [
        _p("ClassA", "fid_a"),
        _p("ClassB", "fid_a"),
        _p("ClassB", "fid_a"),
    ]
    result = problems_matching_class_and_fid(problems, "ClassA", "fid_a")
    assert len(result) == 1, "Only ClassA/fid_a; got " + repr(len(result))
    assert result[0].problem_class == "ClassA"


def test_absent_pair_returns_empty_list() -> None:
    """Absent pair -> [] (not raise, not None)."""
    problems = [_p("ClassA", "fid_a")]
    result = problems_matching_class_and_fid(problems, "ClassA", "NONEXISTENT")
    assert result == [], "Absent pair -> []; got " + repr(result)


def test_preserves_insertion_order() -> None:
    """Results in original insertion order."""
    p1 = _p("ClassA", "fid_a", "HIGH")
    p2 = _p("ClassA", "fid_a", "LOW")
    p3 = _p("ClassA", "fid_b", "HIGH")  # excluded
    p4 = _p("ClassA", "fid_a", "MED")
    result = problems_matching_class_and_fid([p1, p3, p2, p4], "ClassA", "fid_a")
    assert result == [p1, p2, p4], "Order preserved; got " + repr(result)
