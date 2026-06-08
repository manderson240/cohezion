"""Item 512: bottom_class_by_score() -- the single lowest-scoring class name (2026-06-08).

``bottom_class_by_score(problems, weights) -> str | None``:
Returns the class name with the LOWEST total weighted severity score.
Alphabetical tie-break.  None for empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns the LOWEST-scoring class (not highest).
     Kills impl reusing top_class_by_score directly.
  2. None for empty (not raise, not "").
     Kills impl calling min([]) without guard.
  3. Alphabetical tie-break: tied bottom classes -> alphabetically first.
     Kills impl returning arbitrary/last-seen tied class.
  4. Returns str not list.
     Kills impl returning classes_by_total_score[-1] (a list element would still be str,
     but the list itself would fail isinstance check).
  5. Accumulates multi-record scores correctly.
     Kills impl scoring only one record per class.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    bottom_class_by_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_lowest_not_highest() -> None:
    """PRIMARY DISC.: returns LOWEST-scoring class, not highest.

    ClassA=5.0, ClassB=1.0 -> bottom is ClassB.
    Kills impl reusing top_class_by_score.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),   # 5.0
        _p("ClassB", "f2", "LOW"),    # 1.0
    ]
    result = bottom_class_by_score(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "ClassB", "ClassB has lowest score (1.0); got " + repr(result)
    assert result != "ClassA", "Must not return highest-scoring class"


def test_none_for_empty_input() -> None:
    """Empty input -> None (not raise, not "").

    Kills impl calling min() without an empty guard.
    """
    result = bottom_class_by_score([], {"HIGH": 3.0})
    assert result is None, "Empty -> None; got " + repr(result)


def test_alphabetical_tie_break_for_bottom() -> None:
    """Tied bottom scores -> alphabetically first class.

    ClassA=1.0, ClassB=1.0 both tied at bottom -> ClassA (alphabetical).
    Kills impl returning ClassB.
    """
    problems = [
        _p("ClassB", "f1", "LOW"),   # 1.0 tied
        _p("ClassA", "f2", "LOW"),   # 1.0 tied
    ]
    result = bottom_class_by_score(problems, {"LOW": 1.0})
    assert result == "ClassA", "Tie -> alphabetical: ClassA before ClassB; got " + repr(result)


def test_returns_str_not_list() -> None:
    """Returns str, not list.

    Ensures the function signature returns a scalar, not a list.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "LOW")]
    result = bottom_class_by_score(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert not isinstance(result, list), "Must not be a list; got " + repr(result)
    assert isinstance(result, str), "Must be str; got " + repr(type(result))


def test_multi_record_accumulation_bottom() -> None:
    """Multi-record class score accumulates; accumulated class can still be bottom.

    ClassA: LOW(1.0) + LOW(1.0) = 2.0; ClassB: HIGH(5.0) = 5.0; ClassC: LOW(1.0) = 1.0.
    Bottom = ClassC (1.0).
    Kills impl scoring only one record per class.
    """
    problems = [
        _p("ClassA", "f1", "LOW"),
        _p("ClassA", "f2", "LOW"),   # ClassA total = 2.0
        _p("ClassB", "f3", "HIGH"),  # ClassB total = 5.0
        _p("ClassC", "f4", "LOW"),   # ClassC total = 1.0
    ]
    result = bottom_class_by_score(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == "ClassC", "ClassC has lowest (1.0); got " + repr(result)
