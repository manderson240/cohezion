"""Item 441: problems_for_severity() — filter Problem records by severity (2026-06-08).

``problems_for_severity(problems, severity) -> list[Problem]``:
Returns all Problem records whose severity matches the given value.
Case-sensitive match.  Preserves input order.  Empty or no-match -> [].
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: filters on severity field (not problem_class or finding_id).
     Kills impl reusing problems_for_class or problems_for_finding_id.
  2. Preserves insertion order.
     Kills impl returning a set or sorted list.
  3. Returns list[Problem] (actual Problem objects, not strings).
     Kills impl extracting only finding_id or class values.
  4. Unknown severity -> [] (not raise).
     Kills impl that errors on missing key.
  5. Empty -> [] (not raise).
     Kills impl with unguarded access.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_for_severity,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_filters_on_severity_not_class_or_fid() -> None:
    """PRIMARY DISC.: uses severity field, not problem_class or finding_id.

    All problems share class='BUG' and fid='f1'. Only severity differs.
    Kills impl reusing problems_for_class (would return all 5 on class='BUG').
    """
    problems = [
        _p("BUG", "f1", "HIGH"),
        _p("BUG", "f1", "HIGH"),
        _p("BUG", "f1", "LOW"),
        _p("BUG", "f1", "HIGH"),
        _p("BUG", "f1", "LOW"),
    ]
    result = problems_for_severity(problems, "HIGH")
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 3, "3 HIGH records; got " + repr(len(result))
    assert all(isinstance(p, Problem) for p in result), "Must return Problem objects"
    assert all(p.severity == "HIGH" for p in result), "All returned records must have severity=HIGH"


def test_preserves_insertion_order() -> None:
    """Preserves input order (not sorted by any field)."""
    problems = [
        _p("c1", "f3", "LOW"),
        _p("c2", "f1", "HIGH"),
        _p("c3", "f2", "LOW"),
        _p("c4", "f4", "LOW"),
    ]
    result = problems_for_severity(problems, "LOW")
    assert len(result) == 3, "3 LOW records; got " + repr(len(result))
    # Order must be preserved: c1/f3, c3/f2, c4/f4
    assert result[0].finding_id == "f3", "First LOW is f3 (insertion order); got " + repr(result[0])
    assert result[1].finding_id == "f2", "Second LOW is f2; got " + repr(result[1])
    assert result[2].finding_id == "f4", "Third LOW is f4; got " + repr(result[2])


def test_returns_list_of_problem_objects() -> None:
    """Returns list[Problem] (full objects), not strings or ids."""
    problems = [_p("cls", "f1", "MED")]
    result = problems_for_severity(problems, "MED")
    assert len(result) == 1
    assert isinstance(result[0], Problem), "Must be Problem object; got " + repr(type(result[0]))
    assert result[0].finding_id == "f1"
    assert result[0].problem_class == "cls"
    assert result[0].severity == "MED"


def test_unknown_severity_returns_empty() -> None:
    """Unknown severity -> [] (not raise)."""
    problems = [_p("cls", "f1", "HIGH")]
    result = problems_for_severity(problems, "NONEXISTENT")
    assert result == [], "Unknown severity -> []; got " + repr(result)


def test_empty_returns_empty() -> None:
    """Empty input returns [], not raise."""
    result = problems_for_severity([], "HIGH")
    assert result == [], "Empty -> []; got " + repr(result)
    assert isinstance(result, list)
