"""Item 461: severity_max_count() -- max record count across distinct severities (2026-06-08).

``severity_max_count(problems) -> int``:
Returns max(counts.values()).  0 for empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns INT max count (not severity name, not total).
     HIGH=3, LOW=1 -> max=3 (int); most_common_severity() -> 'HIGH' (killed).
     Kills impl reusing most_common_severity (which returns str, not int).
  2. Empty -> 0 (int, not raise).
     Kills impl with unguarded max() call.
  3. Single severity -> that severity's count as int.
     2 HIGH -> max_count=2 (not 1 which would be 'one severity').
  4. max >= mean always (validates max is truly the maximum).
     HIGH=1, LOW=4 -> max=4, mean=2.5; 4 >= 2.5.
     Kills impl returning mean by mistake.
  5. max > min when counts differ (validates max > minimum).
     HIGH=3, LOW=1 -> max=3, min=1; 3 > 1.
     Distinguishes max from min (kills impl conflating them).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_max_count,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_max_count_not_severity_name() -> None:
    """PRIMARY DISC.: returns INT max count, not the most-common severity name.

    HIGH=3, LOW=1.  Maximum count is 3 (int).
    most_common_severity() would return 'HIGH' (str) -- wrong here.
    Kills impl delegating to most_common_severity or returning a string.
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "LOW"),
    ]
    result = severity_max_count(problems)
    assert type(result) is int, "Must return int; got " + repr(type(result))
    assert result == 3, "Maximum count=3; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input -> 0 (int), not raise."""
    result = severity_max_count([])
    assert result == 0, "Empty -> 0; got " + repr(result)
    assert type(result) is int


def test_single_severity_returns_that_count() -> None:
    """Single distinct severity -> its count, not 1."""
    problems = [_p("c", f"f{i}", "HIGH") for i in range(2)]
    result = severity_max_count(problems)
    assert result == 2, "2 HIGH -> max=2; got " + repr(result)


def test_max_geq_mean() -> None:
    """max count >= mean count (max is truly the maximum)."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "LOW"),
        _p("c", "f3", "LOW"),
        _p("c", "f4", "LOW"),
        _p("c", "f5", "LOW"),
    ]
    # HIGH=1, LOW=4; mean=2.5, max=4
    result = severity_max_count(problems)
    assert result == 4, "max count=4; got " + repr(result)
    assert result >= 3, "max must be >= mean (2.5); got " + repr(result)


def test_max_greater_than_min_when_counts_differ() -> None:
    """max > min when severities have different counts."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "LOW"),
    ]
    # HIGH=3, LOW=1; max=3, min=1
    result = severity_max_count(problems)
    assert result == 3, "max=3 for HIGH=3,LOW=1; got " + repr(result)
    assert result > 1, "max must be > min (1) when counts differ; got " + repr(result)
