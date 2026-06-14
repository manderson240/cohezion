"""Item 540: fid_score_range() -- range of fid total scores (2026-06-08).

``fid_score_range(problems, weights) -> float``:
Returns the range (max - min) of per-fid total weighted scores.
0.0 for empty or single fid.  Always >= 0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     Kills impl reusing class_score_range on wrong axis.
  2. Always non-negative: max - min, not min - max.
     Kills impl subtracting in wrong order.
  3. Single fid -> 0.0 (range of one value = 0).
     Kills impl without n<2 guard.
  4. 0.0 for empty (not raise).
     Kills impl without empty guard.
  5. Operates on fid TOTAL scores, not raw per-problem severity values.
     Kills impl computing range over individual problem severity weights.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_range


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_range_not_class_axis() -> None:
    """PRIMARY DISC.: operates on fid totals (not class totals).

    All problems in ONE class, 4 fids with totals [1,1,1,10]:
      fid range = 10.0 - 1.0 = 9.0
      class_score_range would return 0.0 (only 1 class -> max==min)
    Kills impl reusing class_score_range (returns 0.0 for single class).
    """
    problems = [
        _p("SameClass", "fid_a", "LOW"),  # fid_a = 1.0
        _p("SameClass", "fid_b", "LOW"),  # fid_b = 1.0
        _p("SameClass", "fid_c", "LOW"),  # fid_c = 1.0
        _p("SameClass", "fid_d", "HIGH"),  # fid_d = 10.0
    ]
    weights = {"LOW": 1.0, "HIGH": 10.0}
    result = fid_score_range(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # fid range = 10 - 1 = 9.0; class range = 0.0 (1 class)
    assert abs(result - 9.0) < 1e-9, (
        f"Range of fid totals [1,1,1,10] = 9.0; got {result} (0.0 = class_score_range wrong axis)"
    )


def test_result_is_non_negative() -> None:
    """Range = max - min (not min - max): always >= 0.

    Two fids with totals [3.0, 1.0]: range = 3.0 - 1.0 = 2.0 (not -2.0).
    """
    problems = [
        _p("A", "fid_high", "S3"),  # 3.0
        _p("B", "fid_low", "S1"),  # 1.0
    ]
    weights = {"S3": 3.0, "S1": 1.0}
    result = fid_score_range(problems, weights)
    assert result >= 0.0, f"Range must be non-negative; got {result}"
    assert abs(result - 2.0) < 1e-9, f"Range of fid totals [3,1] = 2.0; got {result}"


def test_single_fid_returns_zero() -> None:
    """Single distinct fid -> 0.0 (max == min -> range = 0).

    Even with multiple problems, one distinct fid -> range = 0.
    """
    problems = [
        _p("A", "only_fid", "HIGH"),
        _p("B", "only_fid", "HIGH"),
    ]
    weights = {"HIGH": 10.0}
    result = fid_score_range(problems, weights)
    assert result == 0.0, f"Single fid -> range = 0.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = fid_score_range([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_uses_fid_total_scores_not_individual_severities() -> None:
    """Computes range over per-fid TOTAL scores, not raw severity values.

    fid_a: 2x HIGH(5.0) -> total 10.0; fid_b=1.0; fid_c=0.5.
    Fid totals range = 10.0 - 0.5 = 9.5.
    Individual severity values [0.5, 1.0, 5.0, 5.0]: range = 5.0 - 0.5 = 4.5.
    Kills impl computing range over individual problem severity weights.
    """
    problems = [
        _p("C", "fid_a", "HIGH"),  # +5.0
        _p("C", "fid_a", "HIGH"),  # fid_a total = 10.0
        _p("C", "fid_b", "LOW"),  # fid_b total = 1.0
        _p("C", "fid_c", "V_LOW"),  # fid_c total = 0.5
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0, "V_LOW": 0.5}
    result = fid_score_range(problems, weights)
    # Fid totals [0.5, 1.0, 10.0]: range = 9.5
    # Individual [0.5, 1.0, 5.0, 5.0]: range = 4.5 -- wrong
    assert isinstance(result, float), "Must return float"
    assert abs(result - 9.5) < 1e-9, (
        f"Range of fid totals [0.5,1.0,10.0] = 9.5; got {result} "
        f"(4.5 = individual severity range is wrong)"
    )
