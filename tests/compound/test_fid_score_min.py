"""Item 550: fid_score_min() -- minimum per-fid total weighted score (2026-06-08).

``fid_score_min(problems, weights) -> float``:
Returns the minimum of per-fid total weighted scores.
Identifies the least-burdened fid.  0.0 for empty.
Single fid -> that fid's total.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     One class, three fids [2.0, 5.0, 9.0]:
     class_score_min = class total (single class guard), fid_score_min = 2.0.
     Kills impl reusing class_score_min on wrong axis.
  2. Returns MIN (not max) of fid totals.
     Kills impl reusing fid_score_max (returns max, not min).
  3. Single fid -> that fid's total (not 0.0).
     Kills impl with incorrect n<2 guard.
  4. 0.0 for empty (not raise).
     Kills impl without empty guard.
  5. Operates on fid TOTAL scores, not individual severity weights.
     Fid A: 3x LOW(1.0) -> total 3.0; fid B: 1x HIGH(8.0) -> total 8.0.
     min(3.0, 8.0) = 3.0; NOT min individual severity 1.0.
     Kills impl computing min over raw per-problem severity weights.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_min


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_min_not_class_axis() -> None:
    """PRIMARY DISC.: keyed on FID axis (not class axis).

    All problems in ONE class; three fids with totals [2.0, 5.0, 9.0].
    class_score_min = that class's total (single-class; returns 16.0).
    fid_score_min = 2.0 (minimum fid total).
    Kills impl reusing class_score_min on wrong axis.
    """
    problems = [
        _p("SameClass", "fid_a", "S2"),  # fid_a = 2.0
        _p("SameClass", "fid_b", "S5"),  # fid_b = 5.0
        _p("SameClass", "fid_c", "S9"),  # fid_c = 9.0
    ]
    weights = {"S2": 2.0, "S5": 5.0, "S9": 9.0}
    result = fid_score_min(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # class total = 16.0 (single class); fid min = 2.0 -- must not be 16.0
    assert abs(result - 2.0) < 1e-9, (
        f"Min fid total [2,5,9] = 2.0; got {result} (16.0 = class axis is wrong)"
    )


def test_returns_min_not_max_of_fid_totals() -> None:
    """Returns MIN (not max) of fid totals.

    Two fids [3.0, 10.0]: min=3.0, max=10.0.
    Kills impl reusing fid_score_max (returns 10.0).
    """
    problems = [
        _p("A", "fid_lo", "S3"),  # fid_lo = 3.0
        _p("B", "fid_hi", "S10"),  # fid_hi = 10.0
    ]
    weights = {"S3": 3.0, "S10": 10.0}
    result = fid_score_min(problems, weights)
    assert abs(result - 3.0) < 1e-9, (
        f"Min fid total [3,10] = 3.0; got {result} (10.0 = max is wrong)"
    )


def test_single_fid_returns_its_total() -> None:
    """Single fid -> min = that fid's total (not 0.0).

    Kills impl with incorrect n<2 guard returning 0.0.
    """
    problems = [
        _p("A", "only_fid", "HIGH"),
        _p("B", "only_fid", "LOW"),
    ]
    weights = {"HIGH": 7.0, "LOW": 2.0}
    result = fid_score_min(problems, weights)
    # 1 distinct fid: total = 9.0; min([9.0]) = 9.0
    assert abs(result - 9.0) < 1e-9, (
        f"Single fid total 9.0 -> min = 9.0; got {result} (0.0 = wrong guard)"
    )


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = fid_score_min([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_uses_fid_total_not_individual_severity() -> None:
    """Min of fid TOTALS, not min of individual per-problem severity weights.

    Fid A: 3x LOW(1.0) -> total 3.0; fid B: 1x HIGH(8.0) -> total 8.0.
    Min of fid totals = 3.0 (not 1.0 = min individual severity weight).
    Kills impl computing min over raw per-problem severity weights.
    """
    problems = [
        _p("X", "fid_a", "LOW"),  # +1.0
        _p("X", "fid_a", "LOW"),  # +1.0
        _p("X", "fid_a", "LOW"),  # fid_a total = 3.0
        _p("Y", "fid_b", "HIGH"),  # fid_b total = 8.0
    ]
    weights = {"LOW": 1.0, "HIGH": 8.0}
    result = fid_score_min(problems, weights)
    # fid totals: fid_a=3.0, fid_b=8.0 -> min=3.0
    # individual severity min=1.0 (LOW) -- wrong
    assert abs(result - 3.0) < 1e-9, (
        f"Min fid total = 3.0; got {result} (1.0 = individual severity min is wrong)"
    )
