"""Item 480: problems_matching_fid_and_severity() -- 2-axis fid×severity filter (2026-06-08).

``problems_matching_fid_and_severity(problems, finding_id, severity) -> list[Problem]``:
Returns all Problem objects matching BOTH finding_id AND severity.
Symmetric to problems_matching_class_and_severity on the fid axis.
Complements severity_count_for_fid (which returns int).  Empty list for absent pair.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns Problem objects not int count.
     fid_a/HIGH x2 -> list of 2 Problem objects (not int 2).
     Kills impl reusing severity_count_for_fid which returns int.
  2. Both axes filter: fid_a/HIGH x2, fid_a/LOW x1 -> 2 objects not 3.
     Kills impl filtering only on fid (ignoring severity).
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
    problems_matching_fid_and_severity,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_problem_objects_not_int_count() -> None:
    """PRIMARY DISC.: returns Problem instances, not int count.

    fid_a/HIGH x2 -> list of 2 Problem objects, not int 2.
    Kills impl reusing severity_count_for_fid which returns int.
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassB", "fid_a", "HIGH"),
        _p("ClassA", "fid_b", "HIGH"),
    ]
    result = problems_matching_fid_and_severity(problems, "fid_a", "HIGH")
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 2, "fid_a/HIGH=2; got " + repr(len(result))
    assert all(isinstance(p, Problem) for p in result)
    assert all(p.finding_id == "fid_a" and p.severity == "HIGH" for p in result)


def test_both_axes_filter() -> None:
    """Both fid AND severity filter: fid_a/HIGH x2, fid_a/LOW x1 -> 2 not 3.

    Kills impl filtering only on fid.
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassB", "fid_a", "HIGH"),
        _p("ClassC", "fid_a", "LOW"),
        _p("ClassD", "fid_b", "HIGH"),
    ]
    result = problems_matching_fid_and_severity(problems, "fid_a", "HIGH")
    assert len(result) == 2, "fid_a/HIGH=2 (not 3 total fid_a); got " + repr(len(result))


def test_absent_pair_returns_empty_list() -> None:
    """Absent (fid, severity) pair -> [] (not raise)."""
    problems = [_p("ClassA", "fid_a", "HIGH")]
    result = problems_matching_fid_and_severity(problems, "fid_a", "NONEXISTENT")
    assert result == [], "Absent severity -> []; got " + repr(result)


def test_empty_input_returns_empty_list() -> None:
    """Empty input -> []."""
    result = problems_matching_fid_and_severity([], "fid_a", "HIGH")
    assert result == [], "Empty -> []; got " + repr(result)


def test_preserves_insertion_order() -> None:
    """Returned problems maintain original insertion order."""
    problems = [
        _p("ClassC", "fid_a", "HIGH"),
        _p("ClassA", "fid_b", "HIGH"),
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassB", "fid_a", "HIGH"),
    ]
    result = problems_matching_fid_and_severity(problems, "fid_a", "HIGH")
    classes = [p.problem_class for p in result]
    assert classes == ["ClassC", "ClassA", "ClassB"], (
        "Must preserve insertion order; got " + repr(classes)
    )
