"""Item 457: severity_iqr() -- IQR of severity count distribution (2026-06-08).

``severity_iqr(problems) -> float``:
Returns Q3 - Q1 of the sorted severity count distribution.
0.0 for empty or single-severity.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: IQR = Q3 - Q1 (not std dev -- kills impl reusing severity_z_score).
     Two severities with counts [2, 4] -> IQR=2.0, stdev=1.0 (distinct results).
  2. Single severity -> 0.0 (no spread possible).
     Kills impl without n<=1 guard.
  3. Empty -> 0.0 (not raise).
     Kills impl with unguarded access.
  4. All-equal counts -> 0.0 (Q1 == Q3).
     Kills impl that returns variance instead of IQR.
  5. Non-negative: IQR always >= 0.0.
     Validates Q3 >= Q1 invariant (sorted order guarantee).
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import (
    Problem,
    severity_iqr,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_iqr_not_std_dev() -> None:
    """PRIMARY DISC.: IQR formula (Q3-Q1) distinct from std dev.

    HIGH count=4, MED count=2, LOW count=1 -> sorted counts=[1,2,4].
    Inclusive quartiles: Q1=1.5, Q3=3.0, IQR=1.5.
    Population stdev ≈ 1.247.  Must return 1.5 (IQR), not ~1.247 (stdev).
    Kills impl reusing severity_z_score formula.
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "HIGH"),
        _p("c", "f5", "MED"),
        _p("c", "f6", "MED"),
        _p("c", "f7", "LOW"),
    ]
    result = severity_iqr(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 1.5) < 1e-9, "IQR of [1,2,4] = 1.5; got " + repr(result)


def test_single_severity_returns_zero() -> None:
    """Single distinct severity -> IQR = 0.0 (no spread)."""
    problems = [_p("c", "f1", "HIGH"), _p("d", "f2", "HIGH")]
    result = severity_iqr(problems)
    assert result == 0.0, "Single severity -> 0.0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0.0, not raise."""
    result = severity_iqr([])
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float)


def test_all_equal_counts_returns_zero() -> None:
    """All equal counts: IQR = 0.0 (Q1 == Q3)."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "LOW"),
        _p("c", "f3", "MED"),
    ]
    # counts = {HIGH:1, LOW:1, MED:1} -> sorted=[1,1,1] -> Q1=Q3=1 -> IQR=0
    result = severity_iqr(problems)
    assert result == 0.0, "All equal counts -> IQR=0.0; got " + repr(result)


def test_non_negative() -> None:
    """IQR is always >= 0.0 (Q3 >= Q1 invariant)."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "LOW"),
        _p("c", "f5", "MED"),
        _p("c", "f6", "MED"),
    ]
    result = severity_iqr(problems)
    assert math.isfinite(result), "Must be finite; got " + repr(result)
    assert result >= 0.0, "IQR must be >= 0.0; got " + repr(result)
