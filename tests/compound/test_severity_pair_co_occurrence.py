"""Item 444: severity_pair_co_occurrence() -- fids in both severity_a and severity_b (2026-06-08).

``severity_pair_co_occurrence(problems, severity_a, severity_b) -> int``:
Returns the count of distinct finding_ids that appear in both severity_a's
fid set and severity_b's fid set.  0 for unknown severity or empty.
Symmetric (a,b == b,a).  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: set INTERSECTION over fids filtered by severity
     (not class -- kills impl reusing class_pair_co_occurrence on wrong field).
  2. Returns int (count), not frozenset.
     Kills impl returning the set itself (like class_pair_exclusive_fids).
  3. Symmetric: swap args -> same result.
     Validates commutativity.
  4. Unknown severity -> 0 (not raise).
     Kills impl that errors on missing severity.
  5. Empty -> 0 (not raise).
     Kills impl with unguarded access.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_pair_co_occurrence,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_intersection_over_severity_not_class() -> None:
    """PRIMARY DISC.: set intersection on severity field, not problem_class.

    All problems share class='BUG'. Severities differ.
    fid 'f2' appears in both HIGH and LOW -> co-occurrence = 1.
    Kills impl reusing class_pair_co_occurrence (would count class 'BUG' only).
    """
    problems = [
        _p("BUG", "f1", "HIGH"),
        _p("BUG", "f2", "HIGH"),
        _p("BUG", "f2", "LOW"),
        _p("BUG", "f3", "LOW"),
    ]
    result = severity_pair_co_occurrence(problems, "HIGH", "LOW")
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 1, "Only f2 is in both HIGH and LOW; got " + repr(result)


def test_returns_int_not_set() -> None:
    """Returns int (count), not frozenset like class_pair_exclusive_fids."""
    problems = [_p("c", "f1", "HIGH"), _p("c", "f1", "LOW")]
    result = severity_pair_co_occurrence(problems, "HIGH", "LOW")
    assert isinstance(result, int), "Must be int; got " + repr(type(result))
    assert result == 1, "f1 in both -> count=1; got " + repr(result)


def test_symmetric_swap_gives_same_result() -> None:
    """Swapping severity args gives the same result (commutative)."""
    problems = [
        _p("a", "f1", "HIGH"),
        _p("b", "f2", "HIGH"),
        _p("c", "f2", "LOW"),
        _p("d", "f3", "LOW"),
    ]
    ab = severity_pair_co_occurrence(problems, "HIGH", "LOW")
    ba = severity_pair_co_occurrence(problems, "LOW", "HIGH")
    assert ab == ba, f"Must be symmetric; got ab={ab!r} ba={ba!r}"
    assert ab == 1, "f2 in both HIGH+LOW -> 1; got " + repr(ab)


def test_unknown_severity_returns_zero() -> None:
    """Unknown severity -> 0 (not raise)."""
    problems = [_p("cls", "f1", "HIGH")]
    result = severity_pair_co_occurrence(problems, "HIGH", "NONEXISTENT")
    assert result == 0, "Unknown severity_b -> 0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0, not raise."""
    result = severity_pair_co_occurrence([], "HIGH", "LOW")
    assert result == 0, "Empty -> 0; got " + repr(result)
    assert isinstance(result, int)
