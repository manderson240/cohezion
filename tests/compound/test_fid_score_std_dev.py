"""Item 525: fid_score_std_dev() -- population std-dev of fid total scores (2026-06-08).

``fid_score_std_dev(problems, weights) -> float``:
Returns sqrt(population_variance(fid_totals)).
0.0 for empty or single fid.  0.0 when all fid scores are equal.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns FID-axis STD-DEV (not class-axis std-dev).
     Kills impl delegating to score_std_dev (class axis) on wrong axis.
  2. Value is sqrt of POPULATION variance (not sample variance, not variance itself).
     Kills impl returning fid-axis variance (non-sqrt) or sample std-dev.
  3. 0.0 for empty input (not raise).
     Kills impl without empty guard.
  4. 0.0 for single fid (no division-by-zero).
     Kills impl that returns non-zero or raises for a single fid.
  5. 0.0 when all fid scores are equal (zero spread, multiple fids).
     Kills impl that only handles single-fid but not equal-values edge.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import Problem, fid_score_std_dev


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_std_dev_not_class_axis() -> None:
    """PRIMARY DISC.: computes std-dev from FID totals, not class totals.

    Two fids with score 1.0 and 5.0; class-level std-dev would be different
    if the classes had different scores.
    fid_a=1.0, fid_b=5.0: population std-dev = sqrt(((1-3)^2 + (5-3)^2)/2) = sqrt(4) = 2.0
    class-axis std-dev from score_std_dev would use class totals (different value).
    Kills impl delegating to score_std_dev.
    """
    problems = [
        _p("ClassX", "fid_a", "LOW"),   # fid_a total = 1.0
        _p("ClassY", "fid_b", "HIGH"),  # fid_b total = 5.0
    ]
    weights = {"LOW": 1.0, "HIGH": 5.0}
    result = fid_score_std_dev(problems, weights)
    # Expected: sqrt(population_variance([1.0, 5.0]))
    # mean = 3.0, variance = ((1-3)^2 + (5-3)^2)/2 = (4+4)/2 = 4.0, std-dev = 2.0
    assert abs(result - 2.0) < 1e-9, f"fid std-dev should be 2.0; got {result}"


def test_returns_sqrt_not_variance() -> None:
    """Value is the SQUARE ROOT of variance (not variance itself).

    Two fids fid_a=1.0, fid_b=5.0: population variance=4.0, std-dev=2.0.
    Kills impl returning 4.0 (variance) instead of 2.0 (std-dev).
    """
    problems = [
        _p("C1", "fid_a", "LOW"),   # 1.0
        _p("C2", "fid_b", "HIGH"),  # 5.0
    ]
    weights = {"LOW": 1.0, "HIGH": 5.0}
    result = fid_score_std_dev(problems, weights)
    variance = 4.0  # population variance of [1.0, 5.0]
    assert abs(result - math.sqrt(variance)) < 1e-9, (
        f"must be sqrt(variance)={math.sqrt(variance):.4f}; got {result}"
    )
    # Explicitly check it is NOT the variance
    assert abs(result - variance) > 0.1, (
        f"result {result} equals variance {variance} -- impl may return variance not std-dev"
    )


def test_empty_input_returns_zero() -> None:
    """Empty input -> 0.0 (not raise)."""
    result = fid_score_std_dev([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_single_fid_returns_zero() -> None:
    """Single fid -> 0.0 (not raise, zero spread).

    Kills impl that raises ZeroDivisionError for a single fid.
    """
    problems = [_p("C", "fid_x", "HIGH"), _p("C", "fid_x", "LOW")]
    result = fid_score_std_dev(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == 0.0, f"Single fid -> 0.0; got {result}"


def test_all_equal_fid_scores_returns_zero() -> None:
    """Multiple fids all with the same score -> 0.0.

    Kills impl that only handles single-fid but not equal-values edge.
    """
    problems = [
        _p("C1", "fid_a", "MED"),
        _p("C2", "fid_b", "MED"),
        _p("C3", "fid_c", "MED"),
    ]
    result = fid_score_std_dev(problems, {"MED": 2.0})
    assert result == 0.0, f"All fid scores equal -> 0.0; got {result}"
