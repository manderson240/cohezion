"""Item 537: class_score_mad() -- median absolute deviation of class total scores (2026-06-08).

``class_score_mad(problems, weights) -> float``:
Returns the Median Absolute Deviation (MAD) of per-class total weighted scores.
Formula: MAD = median(abs(xi - median(x))).  Two-step: compute median first, then
median of absolute deviations.  0.0 for empty or single class.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns MAD (not std_dev) of class totals.
     Kills impl reusing score_std_dev (different values; MAD < std_dev for [1,2,3,4]).
  2. Two-step: median of abs deviations (not mean of abs deviations).
     Kills impl computing Mean Absolute Deviation (MAD \!= mean_AD for skewed data).
  3. Single class -> 0.0 (MAD of one value is 0).
     Kills impl with wrong guard that raises or returns non-zero.
  4. 0.0 for empty (not raise).
     Kills impl without empty guard.
  5. Operates on class TOTAL scores, not raw per-problem severity values.
     Kills impl computing MAD over individual problem severity weights.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_mad


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_mad_not_std_dev() -> None:
    """PRIMARY DISC.: returns MAD of class totals, not std_dev.

    Four classes with totals [1.0, 2.0, 3.0, 4.0]:
      median = 2.5
      abs deviations from median: [1.5, 0.5, 0.5, 1.5]
      MAD = median([0.5, 0.5, 1.5, 1.5]) = (0.5 + 1.5) / 2 = 1.0
      std_dev = sqrt(5/4) ≈ 1.118
    Kills impl reusing score_std_dev (returns ~1.118, not 1.0).
    """
    problems = [
        _p("A", "f1", "S1"),  # 1.0
        _p("B", "f2", "S2"),  # 2.0
        _p("C", "f3", "S3"),  # 3.0
        _p("D", "f4", "S4"),  # 4.0
    ]
    weights = {"S1": 1.0, "S2": 2.0, "S3": 3.0, "S4": 4.0}
    result = class_score_mad(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # MAD = 1.0; std_dev ≈ 1.118 — must not be ~1.118
    assert abs(result - 1.0) < 1e-9, (
        f"MAD of class totals [1,2,3,4] = 1.0; got {result} "
        f"(~1.118 = std_dev is wrong)"
    )


def test_median_of_abs_deviations_not_mean() -> None:
    """Two-step: MEDIAN of abs deviations (not MEAN of abs deviations).

    Three classes with totals [1.0, 2.0, 10.0]:
      median = 2.0
      abs deviations: [|1-2|, |2-2|, |10-2|] = [1.0, 0.0, 8.0]
      MAD = median([0.0, 1.0, 8.0]) = 1.0
      mean_AD = (1.0 + 0.0 + 8.0) / 3 = 3.0
    Kills impl computing mean absolute deviation instead of median.
    """
    problems = [
        _p("A", "f1", "S1"),   # 1.0
        _p("B", "f2", "S2"),   # 2.0
        _p("C", "f3", "S10"),  # 10.0
    ]
    weights = {"S1": 1.0, "S2": 2.0, "S10": 10.0}
    result = class_score_mad(problems, weights)
    assert abs(result - 1.0) < 1e-9, (
        f"MAD of class totals [1,2,10] = 1.0; got {result} "
        f"(3.0 = mean_AD is wrong; ~3.78 = mean_AD from global mean is also wrong)"
    )


def test_single_class_returns_zero() -> None:
    """Single class -> 0.0 (MAD of a single value = 0 by definition).

    Kills impl that raises or returns non-zero for n=1.
    """
    problems = [
        _p("OnlyClass", "f1", "HIGH"),
        _p("OnlyClass", "f2", "LOW"),
    ]
    weights = {"HIGH": 10.0, "LOW": 1.0}
    result = class_score_mad(problems, weights)
    # 1 class total = 11.0; MAD([11.0]) = median([|11-11|]) = 0.0
    assert result == 0.0, (
        f"Single class -> MAD = 0.0; got {result}"
    )


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = class_score_mad([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_uses_class_total_scores_not_individual_severities() -> None:
    """Computes MAD over per-class TOTAL scores, not raw severity values.

    Class A: 2x HIGH(5.0) -> total 10.0; B=3.0, C=1.0.
    Class totals [1.0, 3.0, 10.0]: median=3.0, MAD=median([2.0,0.0,7.0])=2.0.
    Individual severities [1.0, 3.0, 5.0, 5.0]: median=4.0, MAD=1.0.
    Kills impl computing MAD over individual problem severity weights.
    """
    problems = [
        _p("A", "f1", "HIGH"),   # +5.0
        _p("A", "f2", "HIGH"),   # A total = 10.0
        _p("B", "f3", "LOW"),    # B total = 3.0
        _p("C", "f4", "V_LOW"),  # C total = 1.0
    ]
    weights = {"HIGH": 5.0, "LOW": 3.0, "V_LOW": 1.0}
    result = class_score_mad(problems, weights)
    # Class totals [1,3,10]: median=3.0, MAD=median([2,0,7])=2.0
    # Individual [1,3,5,5]: median=4.0, MAD=1.0 — wrong
    assert isinstance(result, float), "Must return float"
    assert abs(result - 2.0) < 1e-9, (
        f"MAD of class totals [1,3,10] = 2.0; got {result} "
        f"(1.0 = individual severity MAD is wrong)"
    )
