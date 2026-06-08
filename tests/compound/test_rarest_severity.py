"""Item 453: rarest_severity() -- severity with the lowest record count (2026-06-08).

``rarest_severity(problems) -> str | None``:
Returns the severity string with the fewest Problem records.
Ties broken alphabetically (smallest str wins).  None for empty.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns the ANTI-MODE (least frequent), not mode.
     Kills impl reusing most_common_severity (returning max-count sev).
  2. Tie-breaking alphabetically (ascending): CRITICAL < INFO.
     Kills impl returning an arbitrary tie winner.
  3. None for empty input (not raise, not "").
     Kills impl with unguarded access.
  4. Single-severity -> that severity (length-1 edge case).
     Confirms both None guard and single-entry handling.
  5. All severities equal count -> alphabetically first.
     Validates tie-break when all counts are 1.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    rarest_severity,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_least_frequent_not_most_frequent() -> None:
    """PRIMARY DISC.: returns the least frequent severity, not the most frequent.

    HIGH appears 3 times, LOW appears 1 time.
    rarest_severity must return 'LOW', not 'HIGH'.
    Kills impl reusing most_common_severity (would return 'HIGH').
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "LOW"),
    ]
    result = rarest_severity(problems)
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "LOW", "LOW is rarest (count=1); got " + repr(result)


def test_tie_broken_alphabetically() -> None:
    """Ties broken alphabetically: CRITICAL < INFO (alphabetical ascending)."""
    problems = [
        _p("c", "f1", "CRITICAL"),
        _p("c", "f2", "INFO"),
    ]
    result = rarest_severity(problems)
    assert result == "CRITICAL", "Tie -> alpha first CRITICAL < INFO; got " + repr(result)


def test_empty_returns_none() -> None:
    """Empty input returns None (not raise, not empty string)."""
    result = rarest_severity([])
    assert result is None, "Empty -> None; got " + repr(result)


def test_single_severity_returns_it() -> None:
    """Single distinct severity -> returns that severity."""
    problems = [_p("c", "f1", "HIGH"), _p("d", "f2", "HIGH")]
    result = rarest_severity(problems)
    assert result == "HIGH", "Only severity is HIGH; got " + repr(result)


def test_all_equal_count_returns_alphabetically_first() -> None:
    """All severities with same count -> alphabetically first wins.

    WARNING, INFO, ERROR each appear once -> ERROR (alpha first).
    """
    problems = [
        _p("c", "f1", "WARNING"),
        _p("c", "f2", "INFO"),
        _p("c", "f3", "ERROR"),
    ]
    result = rarest_severity(problems)
    assert result == "ERROR", "All count=1 -> alpha first ERROR; got " + repr(result)
