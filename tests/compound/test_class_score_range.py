"""Item 539: class_score_range() -- range of class total scores (2026-06-08).

``class_score_range(problems, weights) -> float``:
Returns the range (max - min) of per-class total weighted scores.
0.0 for empty or single class.  Always >= 0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns RANGE (max-min), not IQR (Q3-Q1).
     Kills impl reusing class_score_iqr (different value for [1,2,3,4]).
  2. Always non-negative: max - min, not min - max.
     Kills impl computing subtraction in wrong order.
  3. Single class -> 0.0 (range of one value = 0).
     Kills impl without n<2 guard.
  4. 0.0 for empty (not raise).
     Kills impl without empty guard.
  5. Operates on class TOTAL scores, not raw per-problem severity values.
     Kills impl computing range over individual problem severity weights.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_range


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_range_not_iqr() -> None:
    """PRIMARY DISC.: returns range (max-min), not IQR (Q3-Q1).

    Four classes with totals [1.0, 2.0, 3.0, 4.0]:
      range = 4.0 - 1.0 = 3.0
      IQR (exclusive) = Q3(3.75) - Q1(1.25) = 2.5
    Kills impl reusing class_score_iqr (would return 2.5, not 3.0).
    """
    problems = [
        _p("A", "f1", "S1"),  # 1.0
        _p("B", "f2", "S2"),  # 2.0
        _p("C", "f3", "S3"),  # 3.0
        _p("D", "f4", "S4"),  # 4.0
    ]
    weights = {"S1": 1.0, "S2": 2.0, "S3": 3.0, "S4": 4.0}
    result = class_score_range(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # range = 3.0; IQR = 2.5 -- must not be 2.5
    assert abs(result - 3.0) < 1e-9, (
        f"Range of class totals [1,2,3,4] = 3.0; got {result} (2.5 = IQR is wrong)"
    )


def test_result_is_non_negative() -> None:
    """Range = max - min (not min - max): always >= 0.

    Two classes with totals [3.0, 1.0]: range = 3.0 - 1.0 = 2.0 (not -2.0).
    Kills impl subtracting max from min instead of min from max.
    """
    problems = [
        _p("A", "f1", "S3"),  # 3.0
        _p("B", "f2", "S1"),  # 1.0
    ]
    weights = {"S3": 3.0, "S1": 1.0}
    result = class_score_range(problems, weights)
    assert result >= 0.0, f"Range must be non-negative; got {result}"
    assert abs(result - 2.0) < 1e-9, f"Range of [3,1] = max-min = 2.0; got {result}"


def test_single_class_returns_zero() -> None:
    """Single class -> 0.0 (max == min -> range = 0).

    Even with multiple problems, one distinct class -> range = 0.
    Kills impl without the n<2 (or max==min) guard.
    """
    problems = [
        _p("OnlyClass", "f1", "HIGH"),
        _p("OnlyClass", "f2", "HIGH"),
    ]
    weights = {"HIGH": 10.0}
    result = class_score_range(problems, weights)
    assert result == 0.0, f"Single class -> range = 0.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = class_score_range([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_uses_class_total_scores_not_individual_severities() -> None:
    """Computes range over per-class TOTAL scores, not raw severity values.

    Class A: 2x HIGH(5.0) -> total 10.0; B=1.0; C=0.5.
    Class totals range = 10.0 - 0.5 = 9.5.
    Individual severity values [0.5, 1.0, 5.0, 5.0]: range = 5.0 - 0.5 = 4.5.
    Kills impl computing range over individual problem severity weights.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # +5.0
        _p("A", "f2", "HIGH"),  # A total = 10.0
        _p("B", "f3", "LOW"),  # B total = 1.0
        _p("C", "f4", "V_LOW"),  # C total = 0.5
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0, "V_LOW": 0.5}
    result = class_score_range(problems, weights)
    # Class totals [0.5, 1.0, 10.0]: range = 9.5
    # Individual [0.5, 1.0, 5.0, 5.0]: range = 4.5 -- wrong
    assert isinstance(result, float), "Must return float"
    assert abs(result - 9.5) < 1e-9, (
        f"Range of class totals [0.5,1.0,10.0] = 9.5; got {result} "
        f"(4.5 = individual severity range is wrong)"
    )
