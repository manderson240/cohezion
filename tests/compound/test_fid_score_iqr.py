"""Item 528: fid_score_iqr() -- IQR of fid total scores (2026-06-08).

``fid_score_iqr(problems, weights) -> float``:
Returns Q3 - Q1 of fid total weighted scores (interquartile range), using
statistics.quantiles with the default 'exclusive' method.
0.0 for fewer than 4 distinct fids.  Empty -> 0.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FINDING_ID axis (not class axis).
     Kills impl reusing class_score_iqr on the wrong axis.
  2. Returns IQR (Q3 - Q1), not range (max - min).
     Kills impl returning score_spread on fid totals.
  3. 0.0 for fewer than 4 distinct fids.
     Kills impl without the n < 4 guard.
  4. Distinct FID count drives the n < 4 guard (not problem count).
     Kills impl using len(problems) < 4 instead of len(fid_totals) < 4.
  5. Empty -> 0.0 (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_iqr


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_iqr_not_class_axis() -> None:
    """PRIMARY DISC.: operates on fid totals, not class totals.

    Two fids under same class with scores 1.0, 2.0, 3.0, 4.0 (4 distinct fids):
    IQR = 2.5 (exclusive).  Impl reusing class_score_iqr would return 0.0
    (only 1 distinct class), which is wrong.
    Kills impl reusing class_score_iqr on the wrong axis.
    """
    problems = [
        _p("SameClass", "fid_a", "S1"),  # fid_a total = 1.0
        _p("SameClass", "fid_b", "S2"),  # fid_b total = 2.0
        _p("SameClass", "fid_c", "S3"),  # fid_c total = 3.0
        _p("SameClass", "fid_d", "S4"),  # fid_d total = 4.0
    ]
    weights = {"S1": 1.0, "S2": 2.0, "S3": 3.0, "S4": 4.0}
    result = fid_score_iqr(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # class_score_iqr would return 0.0 (1 class < 4), but fid_score_iqr = 2.5
    assert abs(result - 2.5) < 1e-9, (
        f"IQR of fid totals [1,2,3,4] = 2.5; got {result} (0.0 = wrong axis)"
    )


def test_returns_iqr_not_range() -> None:
    """IQR (Q3 - Q1) != range (max - min) for the same data.

    fids with totals [1, 2, 3, 4]: IQR = 2.5, range = 3.0.
    Kills impl returning max_fid_score - min_fid_score (3.0).
    """
    problems = [
        _p("C", "f1", "S1"),  # 1.0
        _p("C", "f2", "S2"),  # 2.0
        _p("C", "f3", "S3"),  # 3.0
        _p("C", "f4", "S4"),  # 4.0
    ]
    weights = {"S1": 1.0, "S2": 2.0, "S3": 3.0, "S4": 4.0}
    result = fid_score_iqr(problems, weights)
    # IQR=2.5 != range=3.0 -- must not return range
    assert abs(result - 2.5) < 1e-9, f"IQR = 2.5; range would be 3.0; got {result}"


def test_fewer_than_four_fids_returns_zero() -> None:
    """< 4 distinct fids -> 0.0 (by convention).

    Kills impl without the n < 4 guard.
    """
    problems = [
        _p("C", "fid_a", "HIGH"),
        _p("C", "fid_b", "LOW"),
        _p("C", "fid_c", "MED"),
    ]
    result = fid_score_iqr(problems, {"HIGH": 5.0, "LOW": 1.0, "MED": 3.0})
    assert result == 0.0, f"3 fids -> 0.0; got {result}"


def test_fid_count_not_problem_count_drives_guard() -> None:
    """n < 4 guard checks distinct FID count, not problem count.

    10 problems all sharing 2 fids -> 0.0 (2 < 4 fids).
    Kills impl using len(problems) < 4 instead of len(fid_totals) < 4.
    """
    problems = [_p("C", "fid_x", "HIGH") for _ in range(5)] + [
        _p("C", "fid_y", "LOW") for _ in range(5)
    ]
    result = fid_score_iqr(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == 0.0, f"2 fids (10 problems) -> 0.0 (< 4 fids); got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = fid_score_iqr([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
