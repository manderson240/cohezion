"""Item 510: top_class_by_score() -- the single highest-scoring class name (2026-06-08).

``top_class_by_score(problems, weights) -> str | None``:
Returns the class name with the highest total weighted severity score.
Alphabetical tie-break.  None for empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns a STRING (not list).
     Kills impl returning classes_by_total_score (list) or top_n_classes_by_score(n=1) (list).
  2. None for empty (not raise, not "").
     Kills impl calling max([]) without guard.
  3. Alphabetical tie-break: tied top classes -> alphabetically first.
     Kills impl returning arbitrary/last-seen tied class.
  4. Returns the class with the HIGHEST total (not lowest, not median).
     Kills impl returning min or middle class.
  5. Accumulates multi-record scores correctly.
     Kills impl that counts only one record per class.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_class_by_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_string_not_list() -> None:
    """PRIMARY DISC.: returns str, not list.

    Kills impl returning classes_by_total_score (list).
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),   # 5.0 -> top
        _p("ClassB", "f2", "LOW"),    # 1.0
    ]
    result = top_class_by_score(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "ClassA", "ClassA highest; got " + repr(result)


def test_none_for_empty_input() -> None:
    """Empty input -> None (not raise, not "").

    Kills impl calling max() without an empty guard.
    """
    result = top_class_by_score([], {"HIGH": 3.0})
    assert result is None, "Empty -> None; got " + repr(result)


def test_alphabetical_tie_break() -> None:
    """Tied top scores -> alphabetically first class.

    ClassA=3.0, ClassB=3.0 -> ClassA (alphabetically first).
    Kills impl returning ClassB or arbitrary choice.
    """
    problems = [
        _p("ClassB", "f1", "HIGH"),   # 3.0 tied
        _p("ClassA", "f2", "HIGH"),   # 3.0 tied
    ]
    result = top_class_by_score(problems, {"HIGH": 3.0})
    assert result == "ClassA", "Tie -> alphabetical: ClassA before ClassB; got " + repr(result)


def test_returns_highest_not_lowest() -> None:
    """Returns the HIGHEST-scoring class, not the lowest.

    Kills impl returning min() or bottom class.
    """
    problems = [
        _p("Low", "f1", "LOW"),    # 1.0
        _p("High", "f2", "HIGH"),  # 5.0
        _p("Mid", "f3", "MED"),    # 3.0
    ]
    result = top_class_by_score(problems, {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0})
    assert result == "High", "Highest-scoring is 'High'; got " + repr(result)
    assert result != "Low", "Must not return lowest class"


def test_multi_record_accumulation() -> None:
    """Multi-record class score accumulates correctly.

    ClassA: HIGH(3.0) + LOW(1.0) = 4.0; ClassB: HIGH(3.0) = 3.0 -> ClassA wins.
    Kills impl scoring only one record per class.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),  # +3.0
        _p("ClassA", "f2", "LOW"),   # +1.0 -> total 4.0
        _p("ClassB", "f3", "HIGH"),  # 3.0
    ]
    result = top_class_by_score(problems, {"HIGH": 3.0, "LOW": 1.0})
    assert result == "ClassA", "ClassA accumulates to 4.0 > ClassB 3.0; got " + repr(result)
