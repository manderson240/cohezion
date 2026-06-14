"""Item 459: severity_mean_count() -- mean record count per distinct severity (2026-06-08).

``severity_mean_count(problems) -> float``:
Returns the arithmetic mean of per-severity record counts.
Equals total_records / distinct_severity_count.  0.0 for empty.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: mean of per-severity counts (not total record count, not severity count).
     HIGH=3, LOW=1 -> distinct=2, total=4, mean=2.0.
     Kills impl returning 4 (total) or 2 (distinct count).
  2. 0.0 for empty (not raise).
     Kills impl with unguarded division.
  3. Single severity -> float equal to that count.
     Validates both single-entry handling and float return type.
  4. Float return type, not int.
     Kills impl that returns integer division result.
  5. Uniform distribution -> each severity's count.
     Confirms formula is count-agnostic (not biased by outliers).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_mean_count,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_mean_of_counts_not_total_or_distinct() -> None:
    """PRIMARY DISC.: mean of per-severity counts \!= total records \!= distinct severities.

    HIGH=3, LOW=1 -> mean = (3+1)/2 = 2.0.
    Total records = 4 (wrong), distinct severities = 2 (wrong).
    Kills impl returning len(problems) or len(distinct_severities).
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "LOW"),
    ]
    result = severity_mean_count(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 2.0) < 1e-9, "Mean of [3,1] = 2.0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0.0, not raise."""
    result = severity_mean_count([])
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float)


def test_single_severity_returns_its_count() -> None:
    """Single distinct severity -> mean = count of that severity."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
    ]
    result = severity_mean_count(problems)
    assert isinstance(result, float), "Must be float; got " + repr(type(result))
    assert abs(result - 3.0) < 1e-9, "Single severity count=3 -> 3.0; got " + repr(result)


def test_returns_float_not_int() -> None:
    """Returns float even when result is an integer value."""
    problems = [_p("c", "f1", "HIGH"), _p("c", "f2", "LOW")]
    result = severity_mean_count(problems)
    assert isinstance(result, float), "Must be float; got " + repr(type(result))
    assert abs(result - 1.0) < 1e-9, "HIGH=1,LOW=1 -> mean=1.0; got " + repr(result)


def test_uniform_distribution_mean_equals_each_count() -> None:
    """Uniform counts: mean equals each severity's count."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "LOW"),
        _p("c", "f4", "LOW"),
    ]
    result = severity_mean_count(problems)
    assert abs(result - 2.0) < 1e-9, "Uniform HIGH=2,LOW=2 -> mean=2.0; got " + repr(result)
