"""Item 486: top_n_classes_by_score() -- top-N classes ranked by severity score (2026-06-08).

``top_n_classes_by_score(problems, weights, n) -> list[str]``:
Returns the N class names with the highest total severity score.
Sorted descending by score; alphabetical tie-break.  n=0 or empty -> [].
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns list of class NAMES not dict.
     Top-2 by score -> ['ClassA', 'ClassB'] (not {'ClassA': 7.0, ...}).
     Kills impl returning all_severity_scores dict directly.
  2. Sorted descending by score (highest first).
     Kills impl returning ascending or unsorted list.
  3. Alphabetical tie-break: equal scores -> alphabetically first class wins.
     Kills impl with unstable/arbitrary sort on ties.
  4. n=0 -> [] (not raise).
     Kills impl not handling n=0.
  5. n > len(classes) -> all classes (not pad with None).
     Kills impl that tries to return exactly n even when fewer classes exist.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_n_classes_by_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_list_of_class_names_not_dict() -> None:
    """PRIMARY DISC.: returns list of str names, not dict.

    top-2 -> ['ClassA', 'ClassB'] (not dict).
    Kills impl returning all_severity_scores.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassA", "f3", "LOW"),
        _p("ClassB", "f4", "HIGH"),
        _p("ClassC", "f5", "LOW"),
    ]
    weights = {"HIGH": 3.0, "LOW": 1.0}
    result = top_n_classes_by_score(problems, weights, n=2)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 2, "n=2 -> 2 items; got " + repr(len(result))
    assert all(isinstance(x, str) for x in result), "Must be strings; got " + repr(result)
    assert result[0] == "ClassA", "ClassA highest (7.0); got " + repr(result)
    assert result[1] == "ClassB", "ClassB second (3.0); got " + repr(result)


def test_sorted_descending_by_score() -> None:
    """Highest score first (descending order).

    ClassZ=5.0, ClassA=3.0, ClassM=1.0 -> ['ClassZ', 'ClassA', 'ClassM'].
    Kills impl returning ascending or unsorted.
    """
    problems = [
        _p("ClassA", "f1", "MED"),
        _p("ClassZ", "f2", "HIGH"),
        _p("ClassM", "f3", "LOW"),
    ]
    result = top_n_classes_by_score(problems, {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0}, n=3)
    assert result == ["ClassZ", "ClassA", "ClassM"], "Descending by score; got " + repr(result)


def test_alphabetical_tie_break() -> None:
    """Equal scores -> alphabetically first class comes first.

    ClassB and ClassA both have score=3.0 -> ClassA before ClassB.
    Kills impl with arbitrary tie-break.
    """
    problems = [
        _p("ClassZ", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
    ]
    result = top_n_classes_by_score(problems, {"HIGH": 3.0}, n=2)
    assert result == ["ClassA", "ClassZ"], "Tie -> alphabetical: ClassA before ClassZ; got " + repr(
        result
    )


def test_n_zero_returns_empty_list() -> None:
    """n=0 -> [] (not raise)."""
    problems = [_p("ClassA", "f1", "HIGH")]
    result = top_n_classes_by_score(problems, {"HIGH": 3.0}, n=0)
    assert result == [], "n=0 -> []; got " + repr(result)


def test_n_larger_than_classes_returns_all() -> None:
    """n > number of classes -> return all classes (no padding)."""
    problems = [_p("ClassA", "f1", "HIGH"), _p("ClassB", "f2", "LOW")]
    result = top_n_classes_by_score(problems, {"HIGH": 3.0, "LOW": 1.0}, n=10)
    assert len(result) == 2, "Only 2 classes; got " + repr(result)
    assert set(result) == {"ClassA", "ClassB"}
