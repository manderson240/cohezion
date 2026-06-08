"""Item 530: fid_score_skewness() -- skewness of fid total scores (2026-06-08).

``fid_score_skewness(problems, weights) -> float``:
Returns the population skewness (third standardized moment) of fid total
weighted scores.  Formula: sum((x-mean)^3) / (n * std_dev^3).
0.0 for empty, < 3 fids, or all-equal scores.  Signed float.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     Kills impl reusing class_score_skewness on wrong axis.
  2. Negative skewness for left-skewed fid data.
     Kills impl returning abs(skewness).
  3. 0.0 for < 3 distinct fids (not raise).
     Kills impl without the n < 3 guard.
  4. 0.0 when all fid scores are equal (std_dev = 0).
     Kills impl that divides by zero std_dev.
  5. Empty -> 0.0 (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_skewness


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_skewness_not_class_axis() -> None:
    """PRIMARY DISC.: operates on fid totals (not class totals).

    All problems in ONE class, but 4 different fids with right-skewed totals.
    class_score_skewness would return 0.0 (only 1 class < 3), but
    fid_score_skewness should return ~1.155 (right-skewed fid distribution).
    Kills impl reusing class_score_skewness on the wrong axis.
    """
    problems = [
        _p("SameClass", "fid_a", "LOW"),   # fid_a = 1.0
        _p("SameClass", "fid_b", "LOW"),   # fid_b = 1.0
        _p("SameClass", "fid_c", "LOW"),   # fid_c = 1.0
        _p("SameClass", "fid_d", "HIGH"),  # fid_d = 10.0
    ]
    weights = {"LOW": 1.0, "HIGH": 10.0}
    result = fid_score_skewness(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # class_score_skewness would be 0.0 (< 3 classes); fid_score_skewness ≈ 1.155
    assert abs(result - 1.1547005383792515) < 1e-9, (
        f"Skewness of fid totals [1,1,1,10] ≈ 1.155; got {result} (0.0 = wrong axis)"
    )


def test_negative_skewness_for_left_skewed_fid_data() -> None:
    """Left-skewed fid distribution -> negative skewness.

    fid totals [10, 10, 10, 1] -> skewness ≈ -1.155.
    Kills impl returning abs(skewness).
    """
    problems = [
        _p("C", "fid_a", "HIGH"),  # 10.0
        _p("C", "fid_b", "HIGH"),  # 10.0
        _p("C", "fid_c", "HIGH"),  # 10.0
        _p("C", "fid_d", "LOW"),   # 1.0
    ]
    weights = {"HIGH": 10.0, "LOW": 1.0}
    result = fid_score_skewness(problems, weights)
    assert result < 0.0, f"Left-skewed fid data must have negative skewness; got {result}"
    assert abs(result - (-1.1547005383792515)) < 1e-9, (
        f"Skewness of [10,10,10,1] ≈ -1.155; got {result}"
    )


def test_fewer_than_three_fids_returns_zero() -> None:
    """< 3 distinct fids -> 0.0 (not raise).

    Kills impl without the n < 3 guard.
    """
    problems = [
        _p("C", "fid_a", "HIGH"),
        _p("C", "fid_b", "LOW"),
    ]
    result = fid_score_skewness(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == 0.0, f"2 fids -> 0.0; got {result}"


def test_all_equal_fid_scores_returns_zero() -> None:
    """All fids at same score -> 0.0 (std_dev = 0, no division error).

    Kills impl that divides by zero std_dev.
    """
    problems = [
        _p("C", "fid_a", "MED"),
        _p("C", "fid_b", "MED"),
        _p("C", "fid_c", "MED"),
    ]
    result = fid_score_skewness(problems, {"MED": 3.0})
    assert result == 0.0, f"All equal fid scores -> std_dev=0 -> 0.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = fid_score_skewness([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
