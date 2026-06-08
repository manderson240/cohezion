"""Item 526: fid_score_variance() -- population variance of fid total scores (2026-06-08).

``fid_score_variance(problems, weights) -> float``:
Returns the population variance of all fid total weighted severity scores.
Empty or single fid -> 0.0.  All equal scores -> 0.0.
Formula: mean(x^2) - mean(x)^2.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns population VARIANCE (not std-dev, not range).
     Kills impl returning fid_score_std_dev (sqrt of variance).
  2. Population variance divides by n, NOT n-1 (sample variance).
     Kills impl using statistics.variance (sample, n-1).
  3. 0.0 for empty input (not raise).
     Kills impl without empty guard.
  4. 0.0 for single fid (trivially zero dispersion).
     Kills impl that raises ZeroDivisionError or returns non-zero.
  5. 0.0 when all fid scores are equal (zero dispersion, multiple fids).
     Kills impl that only checks single-fid but not equal-values edge case.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import Problem, fid_score_variance


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_variance_not_std_dev() -> None:
    """PRIMARY DISC.: returns population variance (not std-dev).

    fid_a=3.0, fid_b=1.0: mean=2.0, variance=1.0, std-dev=1.0.
    The two differ here -- but use fid_a=9.0, fid_b=1.0 for clear separation:
    mean=5.0, variance=16.0, std-dev=4.0.
    Kills impl returning fid_score_std_dev (would return 4.0).
    """
    problems = [
        _p("C", "fid_a", "HIGH"),   # 9.0
        _p("C", "fid_b", "LOW"),    # 1.0
    ]
    weights = {"HIGH": 9.0, "LOW": 1.0}
    result = fid_score_variance(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 16.0) < 1e-9, f"variance=16.0; got {result}"
    assert not math.isclose(result, 4.0, rel_tol=1e-9), "Must not return std-dev (4.0)"


def test_population_variance_not_sample() -> None:
    """Population variance divides by n (not n-1 sample variance).

    fid_a=3.0, fid_b=1.0:
      population variance = ((3-2)^2 + (1-2)^2) / 2 = 1.0
      sample variance     = ((3-2)^2 + (1-2)^2) / 1 = 2.0

    Kills impl using statistics.variance (sample, n-1).
    """
    problems = [
        _p("C", "fid_a", "HIGH"),   # 3.0
        _p("C", "fid_b", "LOW"),    # 1.0
    ]
    weights = {"HIGH": 3.0, "LOW": 1.0}
    result = fid_score_variance(problems, weights)
    assert abs(result - 1.0) < 1e-9, (
        f"population variance=1.0; sample variance would be 2.0; got {result}"
    )


def test_empty_input_returns_zero() -> None:
    """Empty input -> 0.0 (not raise)."""
    result = fid_score_variance([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
    assert isinstance(result, float)


def test_single_fid_returns_zero() -> None:
    """Single fid has zero dispersion -> 0.0.

    Kills impl that raises ZeroDivisionError when n=1.
    """
    problems = [_p("C", "fid_x", "HIGH"), _p("C", "fid_x", "LOW")]
    result = fid_score_variance(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == 0.0, f"Single fid -> 0.0; got {result}"


def test_all_equal_scores_returns_zero() -> None:
    """Multiple fids all with the same score -> 0.0 (zero dispersion).

    Three fids all at 2.0: variance = mean(4,4,4) - mean(2,2,2)^2 = 4 - 4 = 0.
    Kills impl that only checks for single-fid but not equal-values edge.
    """
    problems = [
        _p("C", "fid_a", "MED"),
        _p("C", "fid_b", "MED"),
        _p("C", "fid_c", "MED"),
    ]
    result = fid_score_variance(problems, {"MED": 2.0})
    assert result == 0.0, f"All equal fid scores -> 0.0; got {result}"
