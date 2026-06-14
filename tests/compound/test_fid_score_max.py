"""Item 548: fid_score_max() -- maximum per-fid total weighted score (2026-06-08).

``fid_score_max(problems, weights) -> float``:
Returns max(fid_totals.values()).
0.0 for empty.  Single fid -> that fid total.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     Class A has fid_a=10.0 + fid_b=5.0 (class total 15.0); class B has fid_c=3.0.
     class_score_max = 15.0 (class A dominates); fid_score_max = 10.0 (fid_a tops).
     Kills impl reusing class_score_max (returns 15.0, not 10.0).
  2. Accumulates multiple problems in SAME fid before taking max.
     Two problems in fid_a accumulate to 12.0; max of [12, 5, 3] = 12.0.
     Kills impl taking max of individual problem weights (would return 7.0).
  3. Single fid -> returns that fid's total (not 0.0).
     Kills impl with a wrong n<2 guard.
  4. 0.0 for empty (not raise).
     Kills impl without empty guard.
  5. Equal fid totals -> returns the shared value (not error).
     Kills impl failing on ties.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_max


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_max_not_class_axis() -> None:
    """PRIMARY DISC.: keyed on FID axis, not class axis.

    Class A: fid_a=10.0 + fid_b=5.0 (class total 15.0).
    Class B: fid_c=3.0.
    class_score_max = max(15.0, 3.0) = 15.0.
    fid_score_max = max(10.0, 5.0, 3.0) = 10.0.
    Kills impl reusing class_score_max (returns 15.0, not 10.0).
    """
    problems = [
        _p("A", "fid_a", "HIGH"),  # fid_a = 10.0
        _p("A", "fid_b", "MED"),  # fid_b = 5.0 (class A total = 15.0)
        _p("B", "fid_c", "LOW"),  # fid_c = 3.0
    ]
    weights = {"HIGH": 10.0, "MED": 5.0, "LOW": 3.0}
    result = fid_score_max(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # fid_score_max = 10.0; class_score_max = 15.0 -- must not be 15.0
    assert abs(result - 10.0) < 1e-9, (
        f"Max fid total = 10.0; got {result} (15.0 = class_score_max is wrong axis)"
    )


def test_accumulates_same_fid_before_max() -> None:
    """Multiple problems in same fid accumulate before max.

    fid_a: HIGH(7.0) + LOW(5.0) = 12.0; fid_b=5.0; fid_c=3.0.
    Max of [12, 5, 3] = 12.0.
    Max of individual weights = max(7, 5, 5, 3) = 7.0 (wrong).
    """
    problems = [
        _p("A", "fid_a", "HIGH"),  # fid_a += 7.0
        _p("B", "fid_a", "LOW"),  # fid_a += 5.0 -> fid_a = 12.0
        _p("C", "fid_b", "MED"),  # fid_b = 5.0
        _p("D", "fid_c", "LOW"),  # fid_c = 3.0
    ]
    weights = {"HIGH": 7.0, "MED": 5.0, "LOW": 5.0}
    result = fid_score_max(problems, weights)
    assert abs(result - 12.0) < 1e-9, (
        f"Max of fid totals [12,5,3] = 12.0; got {result} (7.0 = individual max is wrong)"
    )


def test_single_fid_returns_that_total() -> None:
    """Single fid -> returns its total (not 0.0).

    Kills impl with a wrong n<2 guard.
    """
    problems = [
        _p("A", "only_fid", "HIGH"),  # +6.0
        _p("B", "only_fid", "MED"),  # +3.0 -> only_fid = 9.0
    ]
    result = fid_score_max(problems, {"HIGH": 6.0, "MED": 3.0})
    assert abs(result - 9.0) < 1e-9, f"Single fid total 9.0 -> max = 9.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = fid_score_max([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_equal_fid_totals_return_shared_value() -> None:
    """Equal fid totals -> returns the shared value (not error).

    Kills impl failing on ties.
    """
    problems = [
        _p("A", "fid_a", "TIE"),  # fid_a = 4.0
        _p("B", "fid_b", "TIE"),  # fid_b = 4.0
    ]
    result = fid_score_max(problems, {"TIE": 4.0})
    assert abs(result - 4.0) < 1e-9, f"Equal totals [4,4] -> max = 4.0; got {result}"
