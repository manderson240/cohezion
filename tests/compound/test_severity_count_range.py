"""Item 462: severity_count_range() -- range of severity record counts (2026-06-08).

``severity_count_range(problems) -> int``:
Returns max(counts) - min(counts).  0 for empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns INT range max-min (not float IQR or stdev).
     HIGH=5, LOW=1 -> range=4 (int); IQR differs; stdev differs.
     Kills impl reusing severity_iqr (float) or severity_cv (float).
  2. Single severity -> 0 (min == max -> range == 0).
     Kills impl without single-entry guard or that returns count instead.
  3. Empty -> 0 (not raise).
     Kills impl with unguarded min/max calls.
  4. Uniform counts -> 0 (min == max when all counts equal).
     Kills impl that returns variance or std dev.
  5. Returns int not float.
     Explicitly distinguishes from severity_iqr / severity_cv.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_count_range,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_range_not_iqr_or_stdev() -> None:
    """PRIMARY DISC.: range = max - min (INT), distinct from float IQR or stdev.

    HIGH=5, LOW=1. max=5, min=1. range=4 (int).
    severity_iqr([1,5]) \!= 4 and severity_cv([1,5]) \!= 4.
    Kills impl reusing severity_iqr or severity_cv formulas.
    """
    problems = [_p("c", f"f{i}", "HIGH") for i in range(5)] + [_p("c", "f5", "LOW")]
    result = severity_count_range(problems)
    assert type(result) is int, "Must return int; got " + repr(type(result))
    assert result == 4, "range = 5-1 = 4; got " + repr(result)


def test_single_severity_returns_zero() -> None:
    """Single severity: min == max -> range == 0."""
    problems = [_p("c", f"f{i}", "HIGH") for i in range(3)]
    result = severity_count_range(problems)
    assert result == 0, "Single severity -> range=0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input -> 0, not raise."""
    result = severity_count_range([])
    assert result == 0, "Empty -> 0; got " + repr(result)
    assert type(result) is int


def test_uniform_counts_returns_zero() -> None:
    """All equal per-severity counts -> range=0 (min==max)."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "LOW"),
        _p("c", "f3", "MED"),
    ]
    # counts = {HIGH:1, LOW:1, MED:1} -> max-min = 0
    result = severity_count_range(problems)
    assert result == 0, "Uniform counts -> range=0; got " + repr(result)


def test_returns_int_not_float() -> None:
    """Returns int, distinguishes from severity_iqr and severity_cv (both float)."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "LOW"),
    ]
    # HIGH=3, LOW=1; range=2
    result = severity_count_range(problems)
    assert type(result) is int, "Must return int not float; got " + repr(type(result))
    assert result == 2, "range=3-1=2; got " + repr(result)
