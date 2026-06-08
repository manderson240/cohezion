"""Item 479: problems_matching_class_and_severity() -- 2-axis class×severity filter (2026-06-08).

``problems_matching_class_and_severity(problems, problem_class, severity) -> list[Problem]``:
Returns all Problem objects matching BOTH problem_class AND severity.
Complements severity_count_for_class (which returns int).  Empty list for absent pair.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns Problem objects not int count.
     ClassA/HIGH x2 -> list of 2 Problem objects (not int 2).
     Kills impl reusing severity_count_for_class which returns int.
  2. Both axes filter: ClassA/HIGH x2, ClassA/LOW x1 -> 2 objects not 3.
     Kills impl filtering only on class (ignoring severity).
  3. Absent pair -> [] (not raise).
     Kills impl raising KeyError on absent combination.
  4. Empty input -> [].
     Kills impl raising on empty.
  5. Preserves insertion order.
     Kills impl that sorts or reorders.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_matching_class_and_severity,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_problem_objects_not_int_count() -> None:
    """PRIMARY DISC.: returns Problem instances, not int count.

    ClassA/HIGH x2 -> list of 2 Problem objects, not int 2.
    Kills impl reusing severity_count_for_class which returns int.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassB", "f3", "HIGH"),
    ]
    result = problems_matching_class_and_severity(problems, "ClassA", "HIGH")
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 2, "ClassA/HIGH=2; got " + repr(len(result))
    assert all(isinstance(p, Problem) for p in result)
    assert all(p.problem_class == "ClassA" and p.severity == "HIGH" for p in result)


def test_both_axes_filter() -> None:
    """Both class AND severity filter: ClassA/HIGH x2, ClassA/LOW x1 -> 2 not 3.

    Kills impl filtering only on class.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassA", "f3", "LOW"),
        _p("ClassB", "f4", "HIGH"),
    ]
    result = problems_matching_class_and_severity(problems, "ClassA", "HIGH")
    assert len(result) == 2, "ClassA/HIGH=2 (not 3 total ClassA); got " + repr(len(result))


def test_absent_pair_returns_empty_list() -> None:
    """Absent (class, severity) pair -> [] (not raise)."""
    problems = [_p("ClassA", "f1", "HIGH")]
    result = problems_matching_class_and_severity(problems, "ClassA", "NONEXISTENT")
    assert result == [], "Absent severity -> []; got " + repr(result)


def test_empty_input_returns_empty_list() -> None:
    """Empty input -> []."""
    result = problems_matching_class_and_severity([], "ClassA", "HIGH")
    assert result == [], "Empty -> []; got " + repr(result)


def test_preserves_insertion_order() -> None:
    """Returned problems maintain original insertion order."""
    problems = [
        _p("ClassA", "fid_c", "HIGH"),
        _p("ClassB", "fid_x", "HIGH"),
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_b", "HIGH"),
    ]
    result = problems_matching_class_and_severity(problems, "ClassA", "HIGH")
    fids = [p.finding_id for p in result]
    assert fids == ["fid_c", "fid_a", "fid_b"], (
        "Must preserve insertion order; got " + repr(fids)
    )
