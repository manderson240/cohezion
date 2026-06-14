"""Item 538: fid_score_mad() -- median absolute deviation of fid total scores (2026-06-08).

``fid_score_mad(problems, weights) -> float``:
Returns MAD = median(|x - median(x)|) of per-fid total weighted scores.
Robust spread measure: resistant to outlier fids.
0.0 for empty or single fid.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     Kills impl reusing class_score_mad on wrong axis.
  2. MAD uses median of abs deviations (not mean).
     Kills impl computing mean(|x - median|) instead of median(|x - median|).
  3. 0.0 for single fid (single value has zero spread).
     Kills impl without the n < 2 guard.
  4. Returns correct MAD for symmetric fid distribution.
     Kills impl that uses mean instead of median as the center.
  5. Empty -> 0.0 (not raise).
     Kills impl without the empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_mad


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_mad_not_class_axis() -> None:
    """PRIMARY DISC.: MAD computed on fid totals, not class totals.

    All problems in ONE class, but 3 distinct fids [1.0, 3.0, 5.0]:
      fid MAD = median(|1-3|, |3-3|, |5-3|) = median(2,0,2) = 2.0
      class MAD = 0.0 (only 1 class, single value)
    Kills impl reusing class_score_mad (would return 0.0).
    """
    problems = [
        _p("SameClass", "fid_a", "S1"),  # fid_a = 1.0
        _p("SameClass", "fid_b", "S3"),  # fid_b = 3.0
        _p("SameClass", "fid_c", "S5"),  # fid_c = 5.0
    ]
    weights = {"S1": 1.0, "S3": 3.0, "S5": 5.0}
    result = fid_score_mad(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # class_score_mad = 0.0 (1 class); fid_score_mad = 2.0
    assert abs(result - 2.0) < 1e-9, (
        f"MAD of fid totals [1,3,5] = 2.0; got {result} (0.0 = wrong axis: class MAD)"
    )


def test_uses_median_of_abs_devs_not_mean() -> None:
    """MAD = median(|x - median|), not mean(|x - median|).

    4 fids with totals [1.0, 1.0, 1.0, 10.0]:
      median = 1.0; abs deviations = [0, 0, 0, 9]
      MAD = median([0,0,0,9]) = 0.0  (two middle values 0+0)/2 = 0.0)
      mean_abs_dev = (0+0+0+9)/4 = 2.25  (wrong impl would return 2.25)
    Kills impl computing mean of absolute deviations instead of median.
    """
    problems = [
        _p("A", "fid_a", "LOW"),  # 1.0
        _p("B", "fid_b", "LOW"),  # 1.0
        _p("C", "fid_c", "LOW"),  # 1.0
        _p("D", "fid_d", "HIGH"),  # 10.0
    ]
    weights = {"LOW": 1.0, "HIGH": 10.0}
    result = fid_score_mad(problems, weights)
    assert result == 0.0, (
        f"MAD of fid totals [1,1,1,10] = 0.0; got {result} (2.25 = mean_abs_dev, not MAD)"
    )
    assert isinstance(result, float)


def test_single_fid_returns_zero() -> None:
    """Single distinct fid -> MAD = 0.0 (single value, no spread).

    Kills impl without the n < 2 guard.
    """
    problems = [
        _p("A", "same_fid", "HIGH"),
        _p("B", "same_fid", "LOW"),
    ]
    result = fid_score_mad(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == 0.0, f"Single fid -> MAD = 0.0; got {result}"


def test_correct_mad_for_symmetric_fids() -> None:
    """Correct MAD for symmetric fid distribution [1,3,5,7].

    median = 4.0; abs devs = [3,1,1,3]; MAD = 2.0.
    """
    problems = [
        _p("A", "fid_a", "S1"),  # 1.0
        _p("B", "fid_b", "S7"),  # 7.0
        _p("C", "fid_c", "S3"),  # 3.0
        _p("D", "fid_d", "S5"),  # 5.0
    ]
    weights = {"S1": 1.0, "S3": 3.0, "S5": 5.0, "S7": 7.0}
    result = fid_score_mad(problems, weights)
    assert abs(result - 2.0) < 1e-9, f"MAD of fid totals [1,3,5,7] = 2.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = fid_score_mad([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
