"""Item 534: fid_score_cv() -- coefficient of variation of fid total scores (2026-06-08).

``fid_score_cv(problems, weights) -> float``:
Returns CV = std_dev / mean of fid total weighted scores.
0.0 for empty, single fid, or mean==0.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     Kills impl reusing class_score_cv on wrong axis.
  2. Returns RATIO (std_dev/mean), not raw std_dev.
     Kills impl reusing fid_score_std_dev directly.
  3. 0.0 for mean==0.0 (all zero fid weights).
     Kills impl dividing by zero mean.
  4. 0.0 for single fid (std_dev=0).
     Kills impl without the n < 2 guard.
  5. Empty -> 0.0 (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_cv


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_cv_not_class_axis() -> None:
    """PRIMARY DISC.: CV computed on fid totals, not class totals.

    All problems in ONE class, two distinct fids fid_a=1.0, fid_b=5.0:
      mean_fid = 3.0, std_dev_fid = 2.0, CV_fid = 2/3 ≈ 0.6667.
    class_score_cv: only 1 class -> returns 0.0.
    Kills impl reusing class_score_cv on wrong axis (returns 0.0).
    """
    problems = [
        _p("SameClass", "fid_a", "LOW"),  # fid_a = 1.0
        _p("SameClass", "fid_b", "HIGH"),  # fid_b = 5.0
    ]
    weights = {"LOW": 1.0, "HIGH": 5.0}
    result = fid_score_cv(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # class_score_cv returns 0.0 (1 class); fid returns ≈0.6667
    expected = 2.0 / 3.0
    assert abs(result - expected) < 1e-9, (
        f"CV of fid totals [1.0, 5.0] = {expected:.6f}; "
        f"got {result} (0.0 = wrong axis, 2.0 = std_dev not CV)"
    )


def test_returns_ratio_not_raw_std_dev() -> None:
    """Returns std_dev/mean (ratio), not std_dev alone.

    fid totals [4.0, 6.0]: mean=5.0, std_dev=1.0, CV=0.2.
    fid_score_std_dev would return 1.0.
    Kills impl reusing fid_score_std_dev.
    """
    problems = [
        _p("C", "fid_a", "MED_LO"),  # 4.0
        _p("C", "fid_b", "MED_HI"),  # 6.0
    ]
    weights = {"MED_LO": 4.0, "MED_HI": 6.0}
    result = fid_score_cv(problems, weights)
    assert abs(result - 0.2) < 1e-9, (
        f"CV of fid totals [4,6] = 0.2; got {result} (1.0 = raw std_dev, not CV)"
    )


def test_mean_zero_returns_zero() -> None:
    """Mean of fid totals == 0.0 -> CV undefined -> 0.0.

    Kills impl dividing by zero when all fid weights are 0.0.
    """
    problems = [
        _p("A", "fid_a", "UNKNOWN"),
        _p("B", "fid_b", "UNKNOWN"),
    ]
    result = fid_score_cv(problems, {"LOW": 1.0})  # UNKNOWN not in weights -> 0.0
    assert result == 0.0, f"All-zero fid totals -> mean=0 -> CV=0.0; got {result}"


def test_single_fid_returns_zero() -> None:
    """Single distinct fid -> std_dev=0 -> CV=0.0.

    Kills impl without the n < 2 guard.
    """
    problems = [
        _p("A", "same_fid", "HIGH"),
        _p("B", "same_fid", "HIGH"),
    ]
    result = fid_score_cv(problems, {"HIGH": 5.0})
    assert result == 0.0, f"Single fid -> std_dev=0 -> CV=0.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = fid_score_cv([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
