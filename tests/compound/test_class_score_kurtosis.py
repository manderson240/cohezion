"""Item 531: class_score_kurtosis() -- excess kurtosis of class total scores (2026-06-08).

``class_score_kurtosis(problems, weights) -> float``:
Returns the excess kurtosis (fourth standardized moment - 3) of class total
weighted scores.  Excess kurtosis: normal=0.0, heavy-tailed>0, light-tailed<0.
0.0 for empty, < 4 classes, or all-equal scores.  Signed float.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns EXCESS kurtosis (can be negative, = raw - 3).
     Kills impl returning raw 4th moment / variance^2 (always positive >= 0).
  2. Heavy-tailed distribution (outlier) -> positive excess kurtosis.
     Kills impl always returning 0.0 or using wrong sign convention.
  3. 0.0 for < 4 classes (not raise).
     Kills impl without the n < 4 guard.
  4. 0.0 when std_dev == 0 (all equal scores).
     Kills impl that divides by zero std_dev.
  5. Empty -> 0.0 (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_kurtosis


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_excess_kurtosis_not_raw_kurtosis() -> None:
    """PRIMARY DISC.: returns EXCESS kurtosis (= raw - 3), which can be negative.

    Four classes with scores [1, 2, 3, 4]:
      raw kurtosis (4th moment / variance^2) ≈ 1.64 (always >= 0)
      excess kurtosis = 1.64 - 3 ≈ -1.36 (negative for light-tailed)
    Kills impl returning raw kurtosis (would return ~1.64, not ~-1.36).
    """
    problems = [
        _p("A", "f1", "S1"),  # 1.0
        _p("B", "f2", "S2"),  # 2.0
        _p("C", "f3", "S3"),  # 3.0
        _p("D", "f4", "S4"),  # 4.0
    ]
    weights = {"S1": 1.0, "S2": 2.0, "S3": 3.0, "S4": 4.0}
    result = class_score_kurtosis(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # Excess kurtosis ≈ -1.36 (negative); raw kurtosis ≈ 1.64 (positive)
    assert result < 0.0, (
        f"Uniform [1,2,3,4] has light tails: excess kurtosis < 0; got {result}"
    )
    assert abs(result - (-1.3600000000000003)) < 1e-9, (
        f"Excess kurtosis ≈ -1.36; got {result} (raw=1.64 is wrong)"
    )


def test_heavy_tailed_distribution_returns_positive_kurtosis() -> None:
    """Heavy-tailed distribution (outlier) -> positive excess kurtosis.

    Five classes with scores [1, 1, 1, 1, 10]:
      excess kurtosis ≈ 0.25 (positive: heavier tails than normal).
    Kills impl always returning 0.0 or returning negative of the true value.
    """
    problems = [
        _p("A", "f1", "LOW"),   # 1.0
        _p("B", "f2", "LOW"),   # 1.0
        _p("C", "f3", "LOW"),   # 1.0
        _p("D", "f4", "LOW"),   # 1.0
        _p("E", "f5", "HIGH"),  # 10.0
    ]
    weights = {"LOW": 1.0, "HIGH": 10.0}
    result = class_score_kurtosis(problems, weights)
    assert result > 0.0, f"Outlier-heavy [1,1,1,1,10] -> positive kurtosis; got {result}"
    assert abs(result - 0.25) < 1e-9, (
        f"Excess kurtosis ≈ 0.25; got {result}"
    )


def test_fewer_than_four_classes_returns_zero() -> None:
    """< 4 distinct classes -> 0.0 (not raise).

    Kills impl without the n < 4 guard.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("B", "f2", "MED"),
        _p("C", "f3", "LOW"),
    ]
    result = class_score_kurtosis(problems, {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0})
    assert result == 0.0, f"3 classes -> 0.0; got {result}"


def test_all_equal_scores_returns_zero() -> None:
    """All classes at same score -> 0.0 (std_dev = 0, no division error).

    Kills impl that divides by zero std_dev.
    """
    problems = [
        _p("A", "f1", "MED"),
        _p("B", "f2", "MED"),
        _p("C", "f3", "MED"),
        _p("D", "f4", "MED"),
    ]
    result = class_score_kurtosis(problems, {"MED": 3.0})
    assert result == 0.0, f"All equal -> std_dev=0 -> 0.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = class_score_kurtosis([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
