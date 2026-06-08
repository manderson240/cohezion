"""Item 440: top_n_severities() -- top-N most frequent severity levels (2026-06-08).

``top_n_severities(problems, n) -> list[tuple[str, int]]``:
Returns up to n (severity, count) tuples sorted by descending count then ascending severity name.
Empty -> [].  n=0 -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on severity field (not class/fid).
     Kills impl reusing top_n_classes or top_n_finding_ids on wrong field.
  2. Sort order: descending count, ascending severity name for ties.
     Kills impl sorting by name only or count ascending.
  3. Returns list[tuple[str, int]] not dict.
     Validates the structural type of the return value.
  4. n=0 -> [] (not raise or full list).
     Kills impl that ignores n=0 edge case.
  5. Empty -> [] (not raise).
     Kills impl with unguarded access.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_n_severities,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_keyed_on_severity_not_class() -> None:
    """PRIMARY DISC.: top_n_severities uses severity field, not class/fid.

    All problems have same class 'BUG' and same fid 'f1', but distinct severities.
    Kills impl reusing top_n_classes which would count 'BUG' only.
    """
    problems = [
        _p("BUG", "f1", "HIGH"),
        _p("BUG", "f1", "HIGH"),
        _p("BUG", "f1", "HIGH"),
        _p("BUG", "f1", "LOW"),
        _p("BUG", "f1", "LOW"),
    ]
    result = top_n_severities(problems, 2)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 2, "n=2 -> 2 items; got " + repr(len(result))
    # Top severity is HIGH (count=3), second is LOW (count=2)
    assert result[0] == ("HIGH", 3), "First = (HIGH, 3); got " + repr(result[0])
    assert result[1] == ("LOW", 2), "Second = (LOW, 2); got " + repr(result[1])


def test_sort_order_descending_count_then_ascending_name() -> None:
    """Tie in count -> ascending severity name (alphabetical) breaks tie."""
    problems = [
        _p("cls", "f1", "CRITICAL"),
        _p("cls", "f2", "INFO"),
        _p("cls", "f3", "WARNING"),
        _p("cls", "f4", "WARNING"),
    ]
    # CRITICAL=1, INFO=1, WARNING=2 -> WARNING first, then CRITICAL, then INFO (alpha tie-break)
    result = top_n_severities(problems, 3)
    assert result[0] == ("WARNING", 2), "WARNING has highest count; got " + repr(result[0])
    assert result[1][0] == "CRITICAL", "Alpha tie-break: CRITICAL < INFO; got " + repr(result[1])
    assert result[2][0] == "INFO", "Alpha tie-break: INFO last; got " + repr(result[2])


def test_returns_list_of_tuples() -> None:
    """Returns list[tuple[str, int]], not dict."""
    problems = [_p("cls", "f1", "HIGH")]
    result = top_n_severities(problems, 1)
    assert isinstance(result, list), "Must be list; got " + repr(type(result))
    assert isinstance(result[0], tuple), "Elements must be tuples; got " + repr(type(result[0]))
    assert result[0] == ("HIGH", 1), "Tuple is (severity, count); got " + repr(result[0])


def test_n_zero_returns_empty_list() -> None:
    """n=0 returns [], not the full list."""
    problems = [_p("cls", "f1", "HIGH"), _p("cls", "f2", "LOW")]
    result = top_n_severities(problems, 0)
    assert result == [], "n=0 -> []; got " + repr(result)


def test_empty_returns_empty_list() -> None:
    """Empty input returns [], not raise."""
    result = top_n_severities([], 5)
    assert result == [], "Empty -> []; got " + repr(result)
    assert isinstance(result, list)
