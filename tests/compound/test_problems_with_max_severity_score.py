"""Item 500: problems_with_max_severity_score() -- records at the global maximum weight (2026-06-08).

``problems_with_max_severity_score(problems, weights) -> list[Problem]``:
Returns all Problem objects whose per-record severity weight equals the global
maximum per-record weight across all problems.  Preserves insertion order.
Ties are ALL included.  Empty -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns list of Problem OBJECTS not class names.
     Kills impl returning all_severity_scores or top_n_classes_by_score.
  2. ALL ties at max weight are included (not just first one).
     Kills impl returning only the first maximum record.
  3. Insertion order is preserved among the returned records.
     Kills impl that sorts by class or severity.
  4. Empty problems -> [] (not raise).
     Kills impl without empty guard.
  5. Unknown-severity problem included when 0.0 IS the global max.
     Kills impl treating unknown-severity records as always excluded.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_with_max_severity_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_list_of_problem_objects_not_names() -> None:
    """PRIMARY DISC.: returns list[Problem], not list of class names.

    Kills impl returning all_severity_scores or top_n_classes_by_score.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassB", "f2", "LOW"),
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = problems_with_max_severity_score(problems, weights)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 1, "Only one HIGH record; got " + repr(len(result))
    assert isinstance(result[0], Problem), "Items must be Problem; got " + repr(result[0])
    assert result[0].problem_class == "ClassA", "ClassA is the max; got " + repr(result[0])


def test_all_ties_at_max_included() -> None:
    """ALL ties at max weight are returned, not just the first.

    Kills impl returning only the first max record (e.g. ``next(...)``).
    """
    p1 = _p("ClassA", "f1", "HIGH")
    p2 = _p("ClassB", "f2", "LOW")
    p3 = _p("ClassC", "f3", "HIGH")
    problems = [p1, p2, p3]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = problems_with_max_severity_score(problems, weights)
    assert len(result) == 2, "Both HIGH records returned; got " + repr(result)
    assert set(result) == {p1, p3}, "ClassA and ClassC; got " + repr(result)


def test_preserves_insertion_order() -> None:
    """Records at max weight are returned in original insertion order.

    Kills impl that sorts by class name or severity label.
    """
    p1 = _p("Z", "f1", "HIGH")
    p2 = _p("A", "f2", "LOW")  # excluded
    p3 = _p("M", "f3", "HIGH")
    problems = [p1, p2, p3]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = problems_with_max_severity_score(problems, weights)
    assert result == [p1, p3], "Insertion order Z before M; got " + repr(result)


def test_empty_problems_returns_empty_list() -> None:
    """Empty input -> [] (not raise)."""
    result = problems_with_max_severity_score([], {"HIGH": 3.0})
    assert result == [], "Empty -> []; got " + repr(result)


def test_unknown_severity_included_when_zero_is_global_max() -> None:
    """Unknown-severity (weight 0.0) included when 0.0 IS the global max.

    When all problems have unknown severities (not in weights), every problem
    gets weight 0.0 and ALL are at the global max.
    Kills impl that silently excludes zero-weight records.
    """
    p1 = _p("ClassA", "f1", "MYSTERY")
    p2 = _p("ClassB", "f2", "GHOST")
    problems = [p1, p2]
    weights: dict[str, float] = {}  # no known severities -> all weights = 0.0
    result = problems_with_max_severity_score(problems, weights)
    assert len(result) == 2, "Both unknown-severity records at max=0.0; got " + repr(result)
    assert set(result) == {p1, p2}
