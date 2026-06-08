"""Item 520: score_variance() -- population variance of class total scores (2026-06-08).

``score_variance(problems, weights) -> float``:
Returns the population variance of all class total weighted scores.
Empty or single class -> 0.0.  All equal scores -> 0.0.
Formula: mean(x^2) - mean(x)^2.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns VARIANCE not RANGE/SPREAD.
     Kills impl returning score_spread (max-min) instead of variance.
  2. Population variance (divide by n, NOT n-1 sample variance).
     Kills impl using statistics.variance (divides by n-1).
  3. 0.0 for empty input (not raise).
     Kills impl without empty guard.
  4. 0.0 for single class (trivially zero dispersion).
     Kills impl that raises ZeroDivisionError or returns non-zero.
  5. 0.0 when all class scores are equal (zero dispersion, multiple classes).
     Kills impl that only checks single-class but not equal-values edge case.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, score_variance


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_variance_not_range() -> None:
    """PRIMARY DISC.: returns population variance (not range/spread).

    Two classes A=3.0, B=1.0:
      mean = 2.0
      variance = mean(x^2) - mean(x)^2 = (9+1)/2 - 4 = 5 - 4 = 1.0
      range   = max - min = 3 - 1 = 2.0

    Kills impl returning score_spread (which would return 2.0).
    """
    problems = [
        _p("A", "f1", "HIGH"),  # 3.0
        _p("B", "f2", "LOW"),   # 1.0
    ]
    weights = {"HIGH": 3.0, "LOW": 1.0}
    result = score_variance(problems, weights)
    assert abs(result - 1.0) < 1e-9, (
        f"variance must be 1.0 (not range=2.0); got {result}"
    )


def test_population_variance_not_sample() -> None:
    """Population variance divides by n (not n-1 sample variance).

    Two classes A=3.0, B=1.0:
      population variance = 1.0  (divides by 2)
      sample variance     = 2.0  (divides by 1 = n-1)

    Kills impl using statistics.variance (sample, n-1).
    """
    problems = [
        _p("A", "f1", "HIGH"),  # 3.0
        _p("B", "f2", "LOW"),   # 1.0
    ]
    weights = {"HIGH": 3.0, "LOW": 1.0}
    result = score_variance(problems, weights)
    # Population variance must be 1.0, not 2.0 (sample)
    assert abs(result - 1.0) < 1e-9, (
        f"population variance=1.0; sample variance would be 2.0; got {result}"
    )


def test_empty_input_returns_zero() -> None:
    """Empty input -> 0.0 (not raise)."""
    result = score_variance([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_single_class_returns_zero() -> None:
    """Single class has zero dispersion -> 0.0.

    Kills impl that raises ZeroDivisionError when n=1.
    """
    problems = [_p("A", "f1", "HIGH"), _p("A", "f2", "HIGH")]
    result = score_variance(problems, {"HIGH": 5.0})
    assert result == 0.0, f"Single class -> 0.0; got {result}"


def test_all_equal_scores_returns_zero() -> None:
    """Multiple classes all with the same score -> 0.0 (zero dispersion).

    Three classes all at 2.0: variance = mean(4,4,4) - mean(2,2,2)^2 = 4 - 4 = 0.
    Kills impl that only checks for single-class but not equal-values edge.
    """
    problems = [
        _p("A", "f1", "MED"),
        _p("B", "f2", "MED"),
        _p("C", "f3", "MED"),
    ]
    result = score_variance(problems, {"MED": 2.0})
    assert result == 0.0, f"All equal scores -> 0.0; got {result}"
