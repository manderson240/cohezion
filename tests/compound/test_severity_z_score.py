"""Item 456: severity_z_score() -- z-score of a severity's count (2026-06-08).

``severity_z_score(problems, severity) -> float``:
Returns (count[severity] - mean_count) / stdev_count.
0.0 when stdev=0 (single severity or all counts equal), absent, or empty.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: z-score formula (count - mean) / stdev, NOT rank or percentile.
     Kills impl reusing severity_rank (returns int) or severity_percentile.
  2. Can be negative: below-mean severity has a negative z-score.
     Kills impl that clamps to [0, ...] or returns absolute value.
  3. 0.0 when stdev=0 (all severities have same count).
     Kills impl that raises ZeroDivisionError.
  4. 0.0 for absent severity (not raise).
     Kills impl that errors on missing severity.
  5. 0.0 for empty input (not raise).
     Kills impl with unguarded access.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_z_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_z_score_not_rank_or_percentile() -> None:
    """PRIMARY DISC.: returns z-score float, not rank int or percentile.

    HIGH=6, LOW=2, MED=4. mean=(6+2+4)/3=4, stdev=sqrt(((6-4)^2+(2-4)^2+(4-4)^2)/3)=sqrt(8/3).
    z(HIGH) = (6-4)/sqrt(8/3) > 0.
    Kills impl returning int rank (1) or percentile (100.0) for most common.
    """
    problems = (
        [_p("c", f"f{i}", "HIGH") for i in range(6)]
        + [_p("c", f"f{i + 6}", "LOW") for i in range(2)]
        + [_p("c", f"f{i + 8}", "MED") for i in range(4)]
    )
    result_high = severity_z_score(problems, "HIGH")
    result_low = severity_z_score(problems, "LOW")
    assert isinstance(result_high, float), "Must return float; got " + repr(type(result_high))
    # HIGH is above mean -> positive z-score
    assert result_high > 0.0, "HIGH above mean -> positive z; got " + repr(result_high)
    # LOW is below mean -> negative z-score
    assert result_low < 0.0, "LOW below mean -> negative z; got " + repr(result_low)


def test_below_mean_returns_negative() -> None:
    """Below-mean severity -> negative z-score (not clamped to 0)."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", "LOW"),
    ]
    result = severity_z_score(problems, "LOW")
    assert result < 0.0, "LOW count=1 < mean=2 -> negative z; got " + repr(result)


def test_zero_stdev_returns_zero() -> None:
    """All severities have same count -> stdev=0 -> z-score=0.0."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "LOW"),
    ]
    # HIGH=1, LOW=1 -> mean=1, stdev=0 -> z=0.0
    result_high = severity_z_score(problems, "HIGH")
    result_low = severity_z_score(problems, "LOW")
    assert abs(result_high) < 1e-9, "stdev=0 -> 0.0; got " + repr(result_high)
    assert abs(result_low) < 1e-9, "stdev=0 -> 0.0; got " + repr(result_low)


def test_absent_severity_returns_zero() -> None:
    """Absent severity -> 0.0 (not raise)."""
    problems = [_p("c", "f1", "HIGH")]
    result = severity_z_score(problems, "NONEXISTENT")
    assert abs(result) < 1e-9, "Absent -> 0.0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input -> 0.0 (not raise)."""
    result = severity_z_score([], "HIGH")
    assert isinstance(result, float)
    assert abs(result) < 1e-9, "Empty -> 0.0; got " + repr(result)
