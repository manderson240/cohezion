"""Item 532: fid_score_kurtosis() -- excess kurtosis of fid total scores (2026-06-08).

``fid_score_kurtosis(problems, weights) -> float``:
Returns the excess kurtosis (fourth standardized moment minus 3) of per-fid
total weighted scores.  0.0 for empty, < 4 fids, or std_dev == 0.
Signed float.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     Kills impl reusing class_score_kurtosis on wrong axis.
  2. Returns excess kurtosis (raw - 3, can be negative).
     Kills impl omitting the -3 Fisher correction.
  3. 0.0 for fewer than 4 distinct fids (not raise).
     Kills impl without the n < 4 guard.
  4. 0.0 for uniform fid scores (std_dev == 0 guard).
     Kills impl dividing by zero.
  5. Empty -> 0.0 (not raise).
     Kills impl without the empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_kurtosis


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_excess_kurtosis_not_class_axis() -> None:
    """PRIMARY DISC.: excess kurtosis computed on fid totals, not class totals.

    All problems in ONE class, but 5 distinct fids with leptokurtic distribution
    [1, 1, 1, 1, 10].  class_score_kurtosis would return 0.0 (only 1 class < 4).
    fid_score_kurtosis should return 0.25 (excess kurtosis of [1,1,1,1,10]).
    Kills impl reusing class_score_kurtosis on the wrong axis.
    """
    problems = [
        _p("SameClass", "fid_a", "LOW"),  # 1.0
        _p("SameClass", "fid_b", "LOW"),  # 1.0
        _p("SameClass", "fid_c", "LOW"),  # 1.0
        _p("SameClass", "fid_d", "LOW"),  # 1.0
        _p("SameClass", "fid_e", "HIGH"),  # 10.0
    ]
    weights = {"LOW": 1.0, "HIGH": 10.0}
    result = fid_score_kurtosis(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # class_score_kurtosis returns 0.0 (1 class); fid returns 0.25
    assert abs(result - 0.25) < 1e-9, (
        f"Excess kurtosis of fid totals [1,1,1,1,10] = 0.25; "
        f"got {result} (0.0 = wrong axis, 3.25 = missing -3)"
    )


def test_returns_excess_not_raw_kurtosis() -> None:
    """Excess kurtosis subtracts 3; uniform [1,2,3,4] fids give -1.36.

    Raw kurtosis = 1.64; excess = -1.36.
    Kills impl omitting the -3 Fisher correction (would return 1.64, positive).
    """
    problems = [
        _p("C", "f1", "S1"),  # fid f1 = 1.0
        _p("C", "f2", "S2"),  # fid f2 = 2.0
        _p("C", "f3", "S3"),  # fid f3 = 3.0
        _p("C", "f4", "S4"),  # fid f4 = 4.0
    ]
    weights = {"S1": 1.0, "S2": 2.0, "S3": 3.0, "S4": 4.0}
    result = fid_score_kurtosis(problems, weights)
    assert abs(result - (-1.36)) < 1e-9, (
        f"Excess kurtosis of [1,2,3,4] fid totals = -1.36; got {result} (raw=1.64 is wrong)"
    )
    assert result < 0.0, "Platykurtic fid data must have negative excess kurtosis"


def test_fewer_than_four_fids_returns_zero() -> None:
    """< 4 distinct fids -> 0.0 (not raise).

    Kills impl without the n < 4 guard.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("B", "f2", "LOW"),
        _p("C", "f3", "MED"),
    ]
    result = fid_score_kurtosis(problems, {"HIGH": 5.0, "LOW": 1.0, "MED": 3.0})
    assert result == 0.0, f"3 fids -> 0.0; got {result}"


def test_uniform_fid_scores_returns_zero() -> None:
    """All fids with equal scores -> 0.0 (std_dev = 0 guard).

    Kills impl dividing by zero when all fid totals are equal.
    """
    problems = [
        _p("C", "f1", "MED"),
        _p("C", "f2", "MED"),
        _p("C", "f3", "MED"),
        _p("C", "f4", "MED"),
    ]
    result = fid_score_kurtosis(problems, {"MED": 3.0})
    assert result == 0.0, f"Uniform fid scores -> 0.0; got {result}"
    assert isinstance(result, float)


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = fid_score_kurtosis([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
