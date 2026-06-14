"""Item 460: severity_min_count() -- min record count across distinct severities (2026-06-08).

``severity_min_count(problems) -> int``:
Returns min(counts.values()).  0 for empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns INT minimum count (not severity name, not float).
     HIGH=3, LOW=1 -> min=1 (int); rarest_severity() -> 'LOW' (killed).
     Kills impl reusing rarest_severity (which returns str, not int).
  2. Empty -> 0 (int, not raise).
     Kills impl with unguarded min() call.
  3. Single severity -> that severity's count as int.
     3 HIGH -> min_count=3 (not 1 which would be 'only one severity').
  4. min <= mean always (validates min is truly the minimum).
     HIGH=4, LOW=1 -> min=1, mean=2.5; 1 <= 2.5.
     Kills impl returning mean by mistake.
  5. Returns int, not float.
     Distinguishes from severity_mean_count which returns float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_min_count,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_min_count_not_severity_name() -> None:
    """PRIMARY DISC.: returns INT min count, not the severity name string.

    HIGH=3, LOW=1.  Minimum count is 1 (int).
    rarest_severity() would return 'LOW' (str) -- that is wrong here.
    Kills impl delegating to rarest_severity or returning a string.
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "LOW"),
    ]
    result = severity_min_count(problems)
    assert type(result) is int, "Must return int; got " + repr(type(result))
    assert result == 1, "Minimum count=1; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input -> 0 (int), not raise."""
    result = severity_min_count([])
    assert result == 0, "Empty -> 0; got " + repr(result)
    assert type(result) is int


def test_single_severity_returns_that_count() -> None:
    """Single distinct severity -> its count, not 1.

    3 HIGH-only problems -> min_count = 3 (not 1).
    Kills impl that always returns 1 for single-severity.
    """
    problems = [_p("c", f"f{i}", "HIGH") for i in range(3)]
    result = severity_min_count(problems)
    assert result == 3, "Single severity count=3 -> min=3; got " + repr(result)


def test_min_leq_mean() -> None:
    """min count must be <= mean count (min is truly the minimum)."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "HIGH"),
        _p("c", "f5", "LOW"),
    ]
    # HIGH=4, LOW=1; mean = 2.5, min = 1
    result = severity_min_count(problems)
    assert result == 1, "min count=1; got " + repr(result)
    assert result <= 2, "min must be <= mean (2.5); got " + repr(result)


def test_returns_int_not_float() -> None:
    """Returns int, not float -- distinguishes from severity_mean_count."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "LOW"),
        _p("c", "f4", "LOW"),
    ]
    result = severity_min_count(problems)
    assert type(result) is int, "Must return int not float; got " + repr(type(result))
    assert result == 2, "HIGH=2, LOW=2 -> min=2; got " + repr(result)
