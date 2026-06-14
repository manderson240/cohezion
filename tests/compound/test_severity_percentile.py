"""Item 455: severity_percentile() -- percentile rank of a severity (2026-06-08).

``severity_percentile(problems, severity) -> float``:
Returns the percentile of a severity in the count distribution.
Most common = 100.0.  Rarest = 0.0.  Absent/empty = 0.0.
Pure; no I/O.

Formula: 100.0 * (n_distinct - rank) / (n_distinct - 1)
where rank is 1-based descending count rank.
Edge case: n_distinct = 1 -> 100.0 (only severity, trivially the most common).

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns float percentile (not int rank).
     Kills impl reusing severity_rank which returns an int.
  2. Most common severity -> 100.0.
     Validates top anchor of the percentile scale.
  3. Rarest (unique) severity -> 0.0.
     Validates bottom anchor.
  4. Absent severity -> 0.0 (not raise).
     Kills impl that errors on missing severity.
  5. Empty input -> 0.0 (not raise).
     Kills impl with unguarded access.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_percentile,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_float_not_int() -> None:
    """PRIMARY DISC.: returns float percentile, not int rank.

    HIGH is most common -> severity_rank returns 1 but severity_percentile
    returns 100.0 (a float).
    Kills impl reusing severity_rank (would return 1 not 100.0).
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "LOW"),
    ]
    result = severity_percentile(problems, "HIGH")
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 100.0) < 1e-9, "Most common -> 100.0; got " + repr(result)


def test_most_common_returns_hundred() -> None:
    """Most common severity -> 100.0 (top of scale)."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "LOW"),
    ]
    result = severity_percentile(problems, "HIGH")
    assert abs(result - 100.0) < 1e-9, "Most common -> 100.0; got " + repr(result)


def test_rarest_returns_zero() -> None:
    """Rarest severity (rank = n_distinct) -> 0.0 (bottom of scale)."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "LOW"),
    ]
    # 2 distinct severities. LOW is rarest (rank 2).
    # percentile = 100 * (2 - 2) / (2 - 1) = 0.0
    result = severity_percentile(problems, "LOW")
    assert abs(result - 0.0) < 1e-9, "Rarest -> 0.0; got " + repr(result)


def test_absent_severity_returns_zero() -> None:
    """Absent severity -> 0.0 (not raise)."""
    problems = [_p("c", "f1", "HIGH")]
    result = severity_percentile(problems, "NONEXISTENT")
    assert abs(result - 0.0) < 1e-9, "Absent -> 0.0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input -> 0.0 (not raise, no ZeroDivisionError)."""
    result = severity_percentile([], "HIGH")
    assert isinstance(result, float)
    assert abs(result - 0.0) < 1e-9, "Empty -> 0.0; got " + repr(result)
