"""Item 454: severity_rank() -- 1-based rank of a severity by record count (2026-06-08).

``severity_rank(problems, severity) -> int``:
Returns the 1-based rank of a given severity in descending-count order.
Rank 1 = most common.  Dense rank for ties.  0 for unknown/empty.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns RANK (not count) -- rank 1 for most common.
     Kills impl returning record count for the severity.
  2. Dense rank: two severities with equal count share the same rank.
     Kills impl using row-number rank (no ties).
  3. 0 for unknown severity (not raise).
     Kills impl that errors on absent severity.
  4. 0 for empty input (not raise).
     Kills impl with unguarded access.
  5. Rank increases as severity frequency decreases.
     Validates direction: most common = 1, rarest = N.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_rank,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_rank_not_count() -> None:
    """PRIMARY DISC.: returns RANK (1-based), not the record count.

    HIGH appears 5 times (most common) -> rank 1.
    LOW appears 2 times -> rank 2.
    Kills impl returning count (5 for HIGH instead of 1).
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "HIGH"),
        _p("c", "f5", "HIGH"),
        _p("c", "f6", "LOW"),
        _p("c", "f7", "LOW"),
    ]
    result_high = severity_rank(problems, "HIGH")
    result_low = severity_rank(problems, "LOW")
    assert isinstance(result_high, int), "Must return int; got " + repr(type(result_high))
    assert result_high == 1, "HIGH most common -> rank 1; got " + repr(result_high)
    assert result_low == 2, "LOW second -> rank 2; got " + repr(result_low)


def test_dense_rank_for_ties() -> None:
    """Tied counts share the same rank (dense rank, not row-number rank).

    HIGH=3, INFO=3, LOW=1.
    HIGH and INFO both rank 1; LOW ranks 2 (not 3).
    Kills impl using row-number rank (HIGH=1, INFO=2, LOW=3).
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "INFO"),
        _p("c", "f5", "INFO"),
        _p("c", "f6", "INFO"),
        _p("c", "f7", "LOW"),
    ]
    assert severity_rank(problems, "HIGH") == 1, "HIGH rank 1 (tied)"
    assert severity_rank(problems, "INFO") == 1, "INFO rank 1 (tied with HIGH)"
    assert severity_rank(problems, "LOW") == 2, "LOW rank 2 (after the tie at rank 1)"


def test_unknown_severity_returns_zero() -> None:
    """Unknown severity -> 0 (not raise)."""
    problems = [_p("c", "f1", "HIGH")]
    result = severity_rank(problems, "NONEXISTENT")
    assert result == 0, "Unknown -> 0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0, not raise."""
    result = severity_rank([], "HIGH")
    assert result == 0, "Empty -> 0; got " + repr(result)
    assert isinstance(result, int)


def test_rank_increases_as_frequency_decreases() -> None:
    """Most common = rank 1; rarest = highest rank number."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "MED"),
        _p("c", "f5", "MED"),
        _p("c", "f6", "LOW"),
    ]
    rank_high = severity_rank(problems, "HIGH")
    rank_med = severity_rank(problems, "MED")
    rank_low = severity_rank(problems, "LOW")
    assert rank_high < rank_med < rank_low, (
        "HIGH(count=3) < MED(count=2) < LOW(count=1) in rank; got "
        + repr((rank_high, rank_med, rank_low))
    )
    assert rank_high == 1 and rank_med == 2 and rank_low == 3
