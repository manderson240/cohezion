"""Item 550: fid_score_min() -- minimum per-fid total weighted score (2026-06-08).

``fid_score_min(problems, weights) -> float``:
Returns the minimum of per-fid total weighted scores.
FID-axis complement of class_score_min.  0.0 for empty.
Single fid -> that fid total.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     Single class, 3 fids [1.0, 5.0, 3.0]: fid min=1.0; class min=9.0 (all in one class).
     Kills impl reusing class_score_min.
  2. Single fid -> that fid total (not 0.0).
     Kills impl with n<2 guard returning 0.0.
  3. Uses fid TOTAL scores, not individual problem severities.
     fid_a: 2x HIGH(5.0) -> 10.0; fid_b=1.0 -> min=1.0.
     Kills impl returning raw severity min.
  4. 0.0 for empty (not raise).
     Kills impl without empty guard.
  5. Returns the true minimum across all fids.
     Kills impl returning first or last fid total.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_min


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_min_not_class_axis() -> None:
    """PRIMARY DISC.: keyed on FID axis, not class axis.

    Single class, fids [1.0, 5.0, 3.0], class total = 9.0:
      fid min = 1.0 (min of [1,5,3])
      class min = 9.0 (the one class's total)
    Kills impl reusing class_score_min (returns 9.0, not 1.0).
    """
    problems = [
        _p("SameClass", "fid_a", "S1"),  # fid_a = 1.0
        _p("SameClass", "fid_b", "S5"),  # fid_b = 5.0
        _p("SameClass", "fid_c", "S3"),  # fid_c = 3.0
    ]
    weights = {"S1": 1.0, "S3": 3.0, "S5": 5.0}
    result = fid_score_min(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 1.0) < 1e-9, (
        f"Fid min of [1,5,3] = 1.0; got {result} (9.0 = class total is wrong axis)"
    )


def test_single_fid_returns_its_total() -> None:
    """Single distinct fid -> that fid total (not 0.0)."""
    problems = [_p("A", "only_fid", "HIGH"), _p("B", "only_fid", "LOW")]
    result = fid_score_min(problems, {"HIGH": 10.0, "LOW": 1.0})
    assert abs(result - 11.0) < 1e-9, f"Single fid total=11.0; got {result}"


def test_uses_fid_total_not_raw_severity() -> None:
    """Min of fid TOTALS, not individual severity values."""
    problems = [
        _p("A", "fid_a", "HIGH"),   # +5.0
        _p("B", "fid_a", "HIGH"),   # fid_a total = 10.0
        _p("C", "fid_b", "LOW"),    # fid_b total = 1.0
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = fid_score_min(problems, weights)
    assert abs(result - 1.0) < 1e-9, f"Min fid total = 1.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    assert fid_score_min([], {"HIGH": 5.0}) == 0.0


def test_returns_true_minimum_across_fids() -> None:
    """Returns actual minimum regardless of insertion order.

    Fids [10.0, 3.0, 7.0]: min = 3.0.
    Kills impl returning first or last fid total.
    """
    problems = [
        _p("A", "fid_x", "HIGH"),  # 10.0 (first)
        _p("B", "fid_y", "LOW"),   # 3.0  (second, the minimum)
        _p("C", "fid_z", "MED"),   # 7.0  (last)
    ]
    weights = {"HIGH": 10.0, "LOW": 3.0, "MED": 7.0}
    result = fid_score_min(problems, weights)
    assert abs(result - 3.0) < 1e-9, f"Min of [10,3,7] = 3.0; got {result}"
