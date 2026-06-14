"""Item 449: all_severities() -- sorted list of all distinct severity values (2026-06-08).

``all_severities(problems) -> list[str]``:
Returns a sorted list of all distinct severity values present in at least one
Problem record.  empty -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns a sorted LIST (not set/frozenset).
     Kills impl returning set or unsorted collection.
  2. Deduplication: duplicate severities collapsed to one entry.
     Kills impl returning [p.severity for p in problems] without dedup.
  3. Sorted alphabetically (ascending): A < B < C.
     Kills impl where insertion order determines result.
  4. Empty -> [] (not raise, not None).
     Kills impl with unguarded access.
  5. Single-severity list -> [that severity] (length 1).
     Confirms dedup + list type on trivial input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    all_severities,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_sorted_list_not_set() -> None:
    """PRIMARY DISC.: returns sorted list, not set or unsorted collection.

    Severities HIGH/CRITICAL/LOW must be returned in alphabetical order
    [CRITICAL, HIGH, LOW], not insertion order.
    Kills impl returning set (unordered) or insertion-order list.
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "CRITICAL"),
        _p("c", "f3", "LOW"),
    ]
    result = all_severities(problems)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert result == ["CRITICAL", "HIGH", "LOW"], "Must be sorted; got " + repr(result)


def test_deduplication_collapses_duplicates() -> None:
    """Duplicate severity values collapse to one entry."""
    problems = [
        _p("a", "f1", "HIGH"),
        _p("b", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
    ]
    result = all_severities(problems)
    assert result == ["HIGH"], "3x HIGH -> ['HIGH']; got " + repr(result)


def test_sorted_alphabetically() -> None:
    """Sorted alphabetically: WARNING > INFO alphabetically but INFO < WARNING."""
    problems = [
        _p("c", "f1", "WARNING"),
        _p("c", "f2", "INFO"),
        _p("c", "f3", "ERROR"),
    ]
    result = all_severities(problems)
    assert result == ["ERROR", "INFO", "WARNING"], "Alpha sort; got " + repr(result)


def test_empty_returns_empty_list() -> None:
    """Empty input returns [], not raise."""
    result = all_severities([])
    assert result == [], "Empty -> []; got " + repr(result)
    assert isinstance(result, list)


def test_single_severity_returns_singleton_list() -> None:
    """Single distinct severity -> list of length 1."""
    problems = [_p("c", "f1", "LOW"), _p("d", "f2", "LOW")]
    result = all_severities(problems)
    assert isinstance(result, list)
    assert len(result) == 1, "One distinct severity -> len 1; got " + repr(result)
    assert result[0] == "LOW", "Must be LOW; got " + repr(result[0])
