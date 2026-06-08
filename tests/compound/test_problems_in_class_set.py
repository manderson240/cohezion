"""Item 371: problems_in_class_set() -- filter problems by class membership (2026-06-08).

``problems_in_class_set(problems, class_set) -> list[Problem]``:
Returns all Problem objects whose problem_class is in the given set of class names.
Generalises problems_for_class to multiple classes at once.  Order preserved.
Empty problems -> [].  Empty class_set -> [].  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: filters by SET MEMBERSHIP, not prefix or single-class equality.
     Kills impl delegating to problems_with_class_prefix or problems_for_class.
  2. Empty class_set returns [] not all problems.
     Kills impl treating empty set as wildcard.
  3. Original insertion order preserved.
     Kills impl that reorders.
  4. Empty problems returns [].
     Kills impl raising on empty.
  5. Returns Problem objects, not class name strings.
     Kills impl returning [p.problem_class for ...].
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_in_class_set,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_filters_by_set_membership_not_prefix() -> None:
    """Filters by membership in the set, not by prefix or single class.

    PRIMARY DISCRIMINATOR: class_set={sec, perf} picks exactly those two classes.
    Kills impl that uses problems_with_class_prefix or single-equality.
    """
    problems = [
        _p("sec", "CVE-001"),
        _p("perf", "PERF-001"),
        _p("style", "STY-001"),
        _p("sec", "CVE-002"),
    ]
    result = problems_in_class_set(problems, frozenset({"sec", "perf"}))
    assert len(result) == 3, "sec×2 + perf×1 = 3; got " + repr(len(result))
    assert all(p.problem_class in {"sec", "perf"} for p in result)
    assert all(isinstance(p, Problem) for p in result)


def test_empty_class_set_returns_empty() -> None:
    """Empty class_set returns [], not all problems.

    Kills impl treating empty set as wildcard (returning all problems).
    """
    problems = [_p("a", "f:0"), _p("b", "f:1")]
    result = problems_in_class_set(problems, frozenset())
    assert result == [], "Empty class_set -> []; got " + repr(result)


def test_original_order_preserved() -> None:
    """Problems are returned in original insertion order.

    Kills impl that sorts or reorders.
    """
    problems = [_p("c", "f:0"), _p("a", "f:1"), _p("b", "f:2"), _p("d", "f:3")]
    result = problems_in_class_set(problems, frozenset({"c", "b"}))
    assert [p.finding_id for p in result] == ["f:0", "f:2"], "Order preserved; got " + repr(
        [p.finding_id for p in result]
    )


def test_empty_problems_returns_empty() -> None:
    """Empty problems list returns []."""
    assert problems_in_class_set([], frozenset({"a", "b"})) == []


def test_returns_problem_objects_not_strings() -> None:
    """Returns Problem instances, not class name strings.

    Kills impl returning [p.problem_class for p in ...].
    """
    problems = [_p("alpha", "f:0"), _p("beta", "f:1")]
    result = problems_in_class_set(problems, frozenset({"alpha"}))
    assert len(result) == 1
    assert isinstance(result[0], Problem), "Must be Problem; got " + repr(type(result[0]))
    assert result[0].finding_id == "f:0"
