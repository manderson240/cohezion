"""Item 477: problems_for_fid() -- list of Problem records with a specific finding_id (2026-06-08).

``problems_for_fid(problems, finding_id) -> list[Problem]``:
Returns all Problem objects whose finding_id equals the given finding_id (exact match).
Symmetric to problems_for_class on the fid axis.  Unknown fid -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns Problem objects not counts.
     fid_a x3 -> list of 3 Problem objects (not int 3).
     Kills impl reusing problem_count_by_fid.
  2. Returns ONLY records with the requested fid.
     Kills impl returning all problems.
  3. Unknown fid -> [] (not raise).
     Kills impl raising KeyError.
  4. Empty input -> [].
     Kills impl raising on empty.
  5. Preserves insertion order.
     Kills impl that sorts or reorders.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_for_fid,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_problem_objects_not_count() -> None:
    """PRIMARY DISC.: returns Problem instances not int count.

    fid_a appears 3 times; result is list of 3 Problem objects, not int 3.
    Kills impl reusing problem_count_by_fid which returns int.
    """
    problems = [_p("ClassA", "fid_a"), _p("ClassB", "fid_a"), _p("ClassA", "fid_a")]
    result = problems_for_fid(problems, "fid_a")
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 3, "3 fid_a records; got " + repr(len(result))
    assert all(isinstance(p, Problem) for p in result), "Must be Problem objects; got " + repr(result)
    assert all(p.finding_id == "fid_a" for p in result), "All results must match fid_a"


def test_only_requested_fid_returned() -> None:
    """Returns only records with the requested finding_id.

    Kills impl returning all problems.
    fid_a x2, fid_b x1; request fid_a -> only 2 returned.
    """
    problems = [_p("ClassA", "fid_a"), _p("ClassB", "fid_b"), _p("ClassC", "fid_a")]
    result = problems_for_fid(problems, "fid_a")
    assert len(result) == 2, "2 fid_a records; got " + repr(len(result))
    assert all(p.finding_id == "fid_a" for p in result)


def test_unknown_fid_returns_empty_list() -> None:
    """Unknown fid -> [] (not raise)."""
    problems = [_p("ClassA", "fid_a")]
    result = problems_for_fid(problems, "NONEXISTENT_FID")
    assert result == [], "Unknown fid -> []; got " + repr(result)


def test_empty_input_returns_empty_list() -> None:
    """Empty input -> []."""
    result = problems_for_fid([], "fid_a")
    assert result == [], "Empty -> []; got " + repr(result)


def test_preserves_insertion_order() -> None:
    """Returned problems preserve original insertion order.

    fids in order: fid_z, fid_a (skipped), fid_z, fid_z, fid_a (skipped) ->
    classes for fid_z come out in order [ClassA, ClassC, ClassD].
    Kills impl that sorts or reorders.
    """
    problems = [
        _p("ClassA", "fid_z"),
        _p("ClassB", "fid_a"),
        _p("ClassC", "fid_z"),
        _p("ClassD", "fid_z"),
        _p("ClassE", "fid_a"),
    ]
    result = problems_for_fid(problems, "fid_z")
    classes = [p.problem_class for p in result]
    assert classes == ["ClassA", "ClassC", "ClassD"], (
        "Must preserve insertion order; got " + repr(classes)
    )
