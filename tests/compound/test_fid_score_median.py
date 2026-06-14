"""Item 536: fid_score_median() -- median of fid total scores (2026-06-08).

``fid_score_median(problems, weights) -> float``:
Returns the median of per-fid total weighted scores.
For even n, the average of the two middle values (standard median definition).
0.0 for empty.  Single fid returns that fid's total (not 0.0).  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     Kills impl reusing class_score_median on wrong axis.
  2. Even-n fids: average of the two middle values (not lower middle only).
     Kills impl returning sorted[n//2 - 1] alone.
  3. Single fid returns its total score (not 0.0).
     Kills impl with a wrong n < 2 guard.
  4. 0.0 for empty (not raise).
     Kills impl without the empty guard.
  5. Operates on fid TOTAL scores, not raw per-problem severity values.
     Kills impl computing median over individual problem severity weights.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_median


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_median_not_class_axis() -> None:
    """PRIMARY DISC.: operates on fid totals (not class totals).

    All problems in ONE class, 4 different fids with totals [1,1,1,10]:
      class_score_median would return 0.0 (only 1 class -> median = 1 class total = 10+1+1+1=13?
      No -- actually class_score_median returns 13.0 for single class)
    Better contrast: 4 fids [1,1,1,10], 1 class.
      fid_score_median = median([1,1,1,10]) = 1.0
      class_score_median = 13.0 (single class total)
    Kills impl reusing class_score_median (returns 13.0, not 1.0).
    """
    problems = [
        _p("SameClass", "fid_a", "LOW"),  # fid_a = 1.0
        _p("SameClass", "fid_b", "LOW"),  # fid_b = 1.0
        _p("SameClass", "fid_c", "LOW"),  # fid_c = 1.0
        _p("SameClass", "fid_d", "HIGH"),  # fid_d = 10.0
    ]
    weights = {"LOW": 1.0, "HIGH": 10.0}
    result = fid_score_median(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # fid totals [1,1,1,10]: median = avg(1,1) = 1.0; class total = 13.0
    assert abs(result - 1.0) < 1e-9, (
        f"Median of fid totals [1,1,1,10] = 1.0; got {result} (13.0 = class total, not fid median)"
    )


def test_even_fids_returns_average_of_middle_two() -> None:
    """Even n: median = average of the two middle values.

    4 fids with totals [1.0, 2.0, 8.0, 9.0]:
      sorted: [1.0, 2.0, 8.0, 9.0]
      middle two: 2.0 and 8.0 -> median = 5.0
    Kills impl that returns lower middle (2.0) alone.
    """
    problems = [
        _p("C", "fid_a", "S1"),  # 1.0
        _p("C", "fid_b", "S9"),  # 9.0
        _p("C", "fid_c", "S8"),  # 8.0
        _p("C", "fid_d", "S2"),  # 2.0
    ]
    weights = {"S1": 1.0, "S2": 2.0, "S8": 8.0, "S9": 9.0}
    result = fid_score_median(problems, weights)
    assert abs(result - 5.0) < 1e-9, (
        f"Median of fid totals [1,2,8,9] = 5.0; got {result} (2.0 = lower-middle-only is wrong)"
    )


def test_single_fid_returns_its_total() -> None:
    """Single fid -> median = that fid's total score (not 0.0).

    Kills impl with an incorrect n < 2 guard returning 0.0.
    """
    problems = [
        _p("A", "only_fid", "HIGH"),  # +10.0
        _p("B", "only_fid", "LOW"),  # +1.0  total = 11.0
    ]
    weights = {"HIGH": 10.0, "LOW": 1.0}
    result = fid_score_median(problems, weights)
    # 1 distinct fid: only_fid total = 11.0; median of [11.0] = 11.0
    assert abs(result - 11.0) < 1e-9, (
        f"Single fid total 11.0 -> median = 11.0; got {result} (0.0 = wrong n<2 guard)"
    )


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = fid_score_median([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_uses_fid_total_scores_not_individual_severities() -> None:
    """Computes median over per-fid TOTAL scores, not raw severity values.

    fid_a has 2x HIGH(5.0) -> total 10.0; fid_b=3.0, fid_c=1.0.
    Fid totals sorted: [1.0, 3.0, 10.0], n=3 (odd) -> median = 3.0.
    Individual severity values: [1.0, 3.0, 5.0, 5.0], n=4 -> median = 4.0.
    Kills impl computing median over individual problem severity weights.
    """
    problems = [
        _p("C", "fid_a", "HIGH"),  # +5.0
        _p("C", "fid_a", "HIGH"),  # fid_a total = 10.0
        _p("C", "fid_b", "LOW"),  # fid_b total = 3.0
        _p("C", "fid_c", "V_LOW"),  # fid_c total = 1.0
    ]
    weights = {"HIGH": 5.0, "LOW": 3.0, "V_LOW": 1.0}
    result = fid_score_median(problems, weights)
    # Fid totals [1.0, 3.0, 10.0]: odd n=3, median=3.0
    # Individual severities [1.0, 3.0, 5.0, 5.0]: median=4.0 — wrong
    assert isinstance(result, float), "Must return float"
    assert abs(result - 3.0) < 1e-9, (
        f"Median of fid totals [1,3,10] = 3.0; got {result} (4.0 = individual severity is wrong)"
    )
