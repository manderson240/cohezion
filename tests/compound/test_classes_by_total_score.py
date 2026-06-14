"""Item 501: classes_by_total_score() -- all classes ranked descending by total score (2026-06-08).

``classes_by_total_score(problems, weights) -> list[str]``:
Returns ALL class names sorted by total weighted severity score descending.
Alphabetical tie-break.  Empty -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns ALL classes (not top-N like top_n_classes_by_score).
     Four classes -> four names in result.
     Kills impl delegating to top_n_classes_by_score with n=len.
  2. Sorted descending by score (highest first).
     Kills impl returning ascending or unsorted list.
  3. Alphabetical tie-break: equal scores -> alphabetically first class wins.
     Kills impl with unstable/arbitrary sort on ties.
  4. Empty input -> [] (not raise).
     Kills impl without empty guard.
  5. Single class -> [that_class] (trivial rank still works).
     Kills impl that needs >=2 classes to function.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_by_total_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_all_classes_not_top_n() -> None:
    """PRIMARY DISC.: all classes returned, not just top-N.

    4 classes -> 4 names in result.
    Kills impl delegating to top_n_classes_by_score(n=2) or similar.
    """
    problems = [
        _p("D", "f1", "HIGH"),
        _p("C", "f2", "MED"),
        _p("B", "f3", "LOW"),
        _p("A", "f4", "TINY"),
    ]
    weights = {"HIGH": 4.0, "MED": 3.0, "LOW": 2.0, "TINY": 1.0}
    result = classes_by_total_score(problems, weights)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 4, "All 4 classes; got " + repr(result)
    assert all(isinstance(x, str) for x in result), "Items must be str; got " + repr(result)
    assert result == ["D", "C", "B", "A"], "Descending: D>C>B>A; got " + repr(result)


def test_sorted_descending_by_score() -> None:
    """Highest score first (descending order).

    ClassZ=5.0, ClassA=3.0, ClassM=1.0 -> ['ClassZ', 'ClassA', 'ClassM'].
    Kills impl returning ascending or unsorted list.
    """
    problems = [
        _p("ClassA", "f1", "MED"),
        _p("ClassZ", "f2", "HIGH"),
        _p("ClassM", "f3", "LOW"),
    ]
    result = classes_by_total_score(problems, {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0})
    assert result == ["ClassZ", "ClassA", "ClassM"], "Descending by score; got " + repr(result)


def test_alphabetical_tie_break() -> None:
    """Equal scores -> alphabetically first class comes first.

    ClassB and ClassA both score 3.0 -> ClassA before ClassB.
    Kills impl with arbitrary tie-break.
    """
    problems = [
        _p("ClassZ", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassM", "f3", "HIGH"),
    ]
    result = classes_by_total_score(problems, {"HIGH": 3.0})
    assert result == ["ClassA", "ClassM", "ClassZ"], "Tie -> alphabetical; got " + repr(result)


def test_empty_input_returns_empty_list() -> None:
    """Empty input -> [] (not raise)."""
    result = classes_by_total_score([], {"HIGH": 3.0})
    assert result == [], "Empty -> []; got " + repr(result)


def test_single_class_returns_that_class() -> None:
    """Single class -> [class_name]."""
    problems = [_p("OnlyClass", "f1", "HIGH"), _p("OnlyClass", "f2", "LOW")]
    result = classes_by_total_score(problems, {"HIGH": 3.0, "LOW": 1.0})
    assert result == ["OnlyClass"], "Single class; got " + repr(result)
