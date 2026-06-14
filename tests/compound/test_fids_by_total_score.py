"""Item 502: fids_by_total_score() -- all fids ranked descending by total score (2026-06-08).

``fids_by_total_score(problems, weights) -> list[str]``:
Returns ALL finding IDs sorted by total weighted severity score descending.
Alphabetical tie-break.  Empty -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns FID names not class names.
     Kills impl reusing classes_by_total_score on the wrong axis.
  2. Sorted descending by score (highest first).
     Kills impl returning ascending or unsorted order.
  3. Alphabetical tie-break: equal scores -> alphabetically first fid wins.
     Kills impl with arbitrary tie-break.
  4. Empty input -> [] (not raise).
     Kills impl without empty guard.
  5. A fid that appears multiple times accumulates score across those occurrences.
     Kills impl counting each record once ignoring class-level aggregation.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fids_by_total_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_names_not_class_names() -> None:
    """PRIMARY DISC.: returns fid names, not class names.

    Kills impl reusing classes_by_total_score on the class axis.
    """
    problems = [
        _p("ClassA", "fid_high", "HIGH"),
        _p("ClassB", "fid_low", "LOW"),
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = fids_by_total_score(problems, weights)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert "fid_high" in result, "fid_high must be present; got " + repr(result)
    assert "fid_low" in result, "fid_low must be present; got " + repr(result)
    assert "ClassA" not in result, "Must not contain class names; got " + repr(result)
    assert "ClassB" not in result, "Must not contain class names; got " + repr(result)
    assert result[0] == "fid_high", "fid_high highest score; got " + repr(result)


def test_sorted_descending_by_score() -> None:
    """Highest fid score first.

    fid_z=5.0, fid_a=3.0, fid_m=1.0 -> ['fid_z', 'fid_a', 'fid_m'].
    Kills impl returning ascending or unsorted list.
    """
    problems = [
        _p("C1", "fid_a", "MED"),
        _p("C2", "fid_z", "HIGH"),
        _p("C3", "fid_m", "LOW"),
    ]
    result = fids_by_total_score(problems, {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0})
    assert result == ["fid_z", "fid_a", "fid_m"], "Descending by score; got " + repr(result)


def test_alphabetical_tie_break() -> None:
    """Equal scores -> alphabetically first fid comes first.

    fid_z and fid_a both score 3.0 -> fid_a before fid_z.
    Kills impl with arbitrary tie-break.
    """
    problems = [
        _p("C1", "fid_z", "HIGH"),
        _p("C2", "fid_a", "HIGH"),
        _p("C3", "fid_m", "HIGH"),
    ]
    result = fids_by_total_score(problems, {"HIGH": 3.0})
    assert result == ["fid_a", "fid_m", "fid_z"], "Tie -> alphabetical; got " + repr(result)


def test_empty_input_returns_empty_list() -> None:
    """Empty input -> [] (not raise)."""
    result = fids_by_total_score([], {"HIGH": 3.0})
    assert result == [], "Empty -> []; got " + repr(result)


def test_fid_score_accumulates_across_occurrences() -> None:
    """A fid appearing in multiple records accumulates its score.

    fid_x appears twice with HIGH (3.0 each) -> total 6.0.
    fid_y appears once with HIGH (3.0) -> total 3.0.
    Result: ['fid_x', 'fid_y'].
    Kills impl that only scores each fid once.
    """
    problems = [
        _p("ClassA", "fid_x", "HIGH"),
        _p("ClassB", "fid_x", "HIGH"),  # same fid, different class
        _p("ClassC", "fid_y", "HIGH"),
    ]
    result = fids_by_total_score(problems, {"HIGH": 3.0})
    assert result == ["fid_x", "fid_y"], "fid_x accumulates 6.0 > fid_y 3.0; got " + repr(result)
