"""Item 529: class_score_skewness() -- skewness of class total scores (2026-06-08).

``class_score_skewness(problems, weights) -> float``:
Returns the population skewness (third standardized moment) of class total
weighted scores.  Formula: sum((x-mean)^3) / (n * std_dev^3).
0.0 for empty, < 3 classes, or all-equal scores.  Signed float.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns signed SKEWNESS, not variance (always >= 0).
     Kills impl reusing score_variance.
  2. Negative skewness for left-skewed data (outlier on low end).
     Kills impl returning abs(skewness).
  3. 0.0 for < 3 classes (not raise).
     Kills impl without the n < 3 guard.
  4. 0.0 when std_dev == 0 (all equal scores).
     Kills impl that divides by zero std_dev.
  5. Empty -> 0.0 (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import Problem, class_score_skewness


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_skewness_not_variance() -> None:
    """PRIMARY DISC.: returns skewness (~1.15), not variance (15.19).

    Four classes with scores [1, 1, 1, 10]:
      variance ≈ 15.19 (always positive)
      skewness ≈ +1.155 (positive = right-tailed)
    Kills impl reusing score_variance (would return 15.19).
    """
    problems = [
        _p("A", "f1", "LOW"),   # 1.0
        _p("B", "f2", "LOW"),   # 1.0
        _p("C", "f3", "LOW"),   # 1.0
        _p("D", "f4", "HIGH"),  # 10.0
    ]
    weights = {"LOW": 1.0, "HIGH": 10.0}
    result = class_score_skewness(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 1.1547005383792515) < 1e-9, (
        f"Skewness of [1,1,1,10] ≈ 1.155; got {result} (variance=15.19 is wrong)"
    )


def test_negative_skewness_for_left_skewed_data() -> None:
    """Left-skewed distribution (outlier on low end) -> negative skewness.

    [10, 10, 10, 1] has skewness ≈ -1.155.
    Kills impl returning abs(skewness) (would return +1.155).
    """
    problems = [
        _p("A", "f1", "HIGH"),   # 10.0
        _p("B", "f2", "HIGH"),   # 10.0
        _p("C", "f3", "HIGH"),   # 10.0
        _p("D", "f4", "LOW"),    # 1.0
    ]
    weights = {"HIGH": 10.0, "LOW": 1.0}
    result = class_score_skewness(problems, weights)
    assert result < 0.0, f"Left-skewed data must have negative skewness; got {result}"
    assert abs(result - (-1.1547005383792515)) < 1e-9, (
        f"Skewness of [10,10,10,1] ≈ -1.155; got {result}"
    )


def test_fewer_than_three_classes_returns_zero() -> None:
    """< 3 classes -> 0.0 (not raise).

    With < 3 classes, skewness is not meaningful.
    Kills impl without the n < 3 guard.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("B", "f2", "LOW"),
    ]
    result = class_score_skewness(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == 0.0, f"2 classes -> 0.0; got {result}"


def test_all_equal_scores_returns_zero() -> None:
    """All classes at same score -> 0.0 (std_dev = 0, no division error).

    Kills impl that divides by zero std_dev.
    """
    problems = [
        _p("A", "f1", "MED"),
        _p("B", "f2", "MED"),
        _p("C", "f3", "MED"),
    ]
    result = class_score_skewness(problems, {"MED": 3.0})
    assert result == 0.0, f"All equal -> std_dev=0 -> 0.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = class_score_skewness([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
