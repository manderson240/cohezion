"""Item 535: class_score_median() -- median of class total scores (2026-06-08).

``class_score_median(problems, weights) -> float``:
Returns the median of per-class total weighted scores.
For even n, returns the average of the two middle values.
0.0 for empty.  Single class returns that class's total.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns MEDIAN of CLASS totals (not mean).
     Kills impl reusing class_mean_score (different for skewed data).
  2. Even-n classes: average of the two middle values.
     Kills impl returning the lower middle only.
  3. Robust to outliers -- median \!= mean for skewed distributions.
     Kills impl that confuses median with mean.
  4. Single class -> that class's total (not 0.0).
     Kills impl with a wrong n < 2 guard.
  5. Empty -> 0.0 (not raise).
     Kills impl without the empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_median


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_class_median_not_mean() -> None:
    """PRIMARY DISC.: returns median of class totals, not mean.

    4 classes with totals [1.0, 1.0, 1.0, 10.0]:
      mean = 3.25  (impl reusing class_mean_score would return 3.25)
      median = 1.0  (two middle values: 1.0 and 1.0, average = 1.0)
    Kills impl reusing class_mean_score (would return 3.25, not 1.0).
    """
    problems = [
        _p("A", "f1", "LOW"),  # 1.0
        _p("B", "f2", "LOW"),  # 1.0
        _p("C", "f3", "LOW"),  # 1.0
        _p("D", "f4", "HIGH"),  # 10.0
    ]
    weights = {"LOW": 1.0, "HIGH": 10.0}
    result = class_score_median(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # median of [1,1,1,10] = avg of 1.0 and 1.0 = 1.0; mean would be 3.25
    assert abs(result - 1.0) < 1e-9, (
        f"Median of class totals [1,1,1,10] = 1.0; got {result} (3.25 = wrong: mean not median)"
    )


def test_even_classes_returns_average_of_middle_two() -> None:
    """Even n: median = average of the two middle values.

    4 classes with totals [1.0, 2.0, 8.0, 9.0]:
      sorted: [1.0, 2.0, 8.0, 9.0]
      middle two: 2.0 and 8.0 -> median = 5.0
    Kills impl that returns lower middle (2.0) or upper middle (8.0) alone.
    """
    problems = [
        _p("A", "f1", "S1"),  # 1.0
        _p("B", "f2", "S9"),  # 9.0
        _p("C", "f3", "S8"),  # 8.0
        _p("D", "f4", "S2"),  # 2.0
    ]
    weights = {"S1": 1.0, "S2": 2.0, "S8": 8.0, "S9": 9.0}
    result = class_score_median(problems, weights)
    # median = (2.0 + 8.0) / 2 = 5.0
    assert abs(result - 5.0) < 1e-9, (
        f"Median of [1,2,8,9] = 5.0; got {result} (2.0 = lower only; 8.0 = upper only)"
    )


def test_odd_classes_returns_exact_middle_value() -> None:
    """Odd n: exact middle value (no averaging needed).

    3 classes with totals [1.0, 3.0, 5.0]: median = 3.0.
    """
    problems = [
        _p("A", "f1", "S5"),  # 5.0
        _p("B", "f2", "S1"),  # 1.0
        _p("C", "f3", "S3"),  # 3.0
    ]
    weights = {"S1": 1.0, "S3": 3.0, "S5": 5.0}
    result = class_score_median(problems, weights)
    assert abs(result - 3.0) < 1e-9, f"Median of [1,3,5] = 3.0; got {result}"


def test_single_class_returns_its_total() -> None:
    """Single class -> median = that class's total score (not 0.0).

    Kills impl with an incorrect n < 2 guard returning 0.0.
    """
    problems = [
        _p("OnlyClass", "f1", "HIGH"),
        _p("OnlyClass", "f2", "LOW"),
    ]
    weights = {"HIGH": 10.0, "LOW": 1.0}
    result = class_score_median(problems, weights)
    # 1 distinct class: OnlyClass total = 11.0; median of [11.0] = 11.0
    assert abs(result - 11.0) < 1e-9, (
        f"Single class total 11.0 -> median = 11.0; got {result} (0.0 = wrong n<2 guard)"
    )


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = class_score_median([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
