"""Item 458: severity_cv() -- coefficient of variation of severity counts (2026-06-08).

``severity_cv(problems) -> float``:
Returns population_stdev / mean of the severity count distribution.
0.0 for empty, single-severity, or uniform counts.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: CV = stdev/mean (not IQR, not variance).
     HIGH×3, LOW×1 -> counts=[1,3], mean=2, stdev=1, CV=0.5.
     IQR=1.0, variance=1.0.  Must return 0.5 (kills impl returning stdev or IQR).
  2. All-equal counts -> 0.0 (stdev=0 -> CV=0.0, not raise).
     Kills impl with unguarded division.
  3. Empty -> 0.0 (not raise).
     Kills impl with unguarded access.
  4. Single severity -> 0.0 (mean != 0 but stdev=0).
     Validates single-entry short-circuit.
  5. Result is non-negative: CV >= 0.0 always.
     Validates formula direction.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_cv,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_cv_not_iqr_or_variance() -> None:
    """PRIMARY DISC.: CV = stdev/mean, distinct from IQR and variance.

    HIGH count=3, LOW count=1 -> counts=[1,3], mean=2.0, stdev=1.0.
    CV = 1.0 / 2.0 = 0.5.
    IQR of [1,3] = 1.0.  Variance of [1,3] = 1.0.  stdev = 1.0.
    Must return 0.5 (kills impl returning IQR=1.0 or stdev/variance=1.0).
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "LOW"),
    ]
    result = severity_cv(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 0.5) < 1e-9, "CV=0.5 for counts [1,3]; got " + repr(result)


def test_all_equal_counts_returns_zero() -> None:
    """All equal counts: stdev=0 -> CV=0.0 (not ZeroDivisionError)."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "LOW"),
        _p("c", "f3", "MED"),
    ]
    result = severity_cv(problems)
    assert result == 0.0, "Equal counts -> CV=0.0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0.0, not raise."""
    result = severity_cv([])
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float)


def test_single_severity_returns_zero() -> None:
    """Single distinct severity: stdev=0 -> CV=0.0."""
    problems = [_p("c", "f1", "HIGH"), _p("d", "f2", "HIGH")]
    result = severity_cv(problems)
    assert result == 0.0, "Single severity -> 0.0; got " + repr(result)


def test_non_negative() -> None:
    """CV is always >= 0.0."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "LOW"),
        _p("c", "f4", "MED"),
    ]
    result = severity_cv(problems)
    assert result >= 0.0, "CV must be >= 0.0; got " + repr(result)
