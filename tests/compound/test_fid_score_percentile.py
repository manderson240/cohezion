"""Item 523: fid_score_percentile() -- percentile position of a fid (2026-06-08).

``fid_score_percentile(problems, weights, finding_id) -> float | None``:
(count of fids with strictly lower score) / (total fids - 1).
Single fid -> 0.0.  Absent or empty -> None.  Float in [0.0, 1.0].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns FLOAT percentile (e.g., 1.0 for top fid).
     Kills impl returning fid_score_rank (which returns INT 1 for top fid).
  2. Uses STRICTLY LOWER count (not <=, not >=).
     Kills impl where ties inflate the percentile (>= or <= direction error).
  3. 0.0 for single fid (not None -- fid exists, denominator is 1).
     Kills impl returning None when only one fid is present.
  4. None for absent finding_id.
     Kills impl raising KeyError on absent fid.
  5. None for empty problems.
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_percentile


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_float_not_rank() -> None:
    """PRIMARY DISC.: returns float percentile (not integer rank).

    Two fids: fid_high=5.0 (top), fid_low=1.0 (bottom).
    fid_high percentile = 1 strictly-lower / (2-1) = 1.0 (float).
    fid_score_rank would return 1 (integer) for fid_high.
    Kills impl returning fid_score_rank.
    """
    problems = [
        _p("C", "fid_high", "HIGH"),  # 5.0
        _p("C", "fid_low", "LOW"),  # 1.0
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}

    result_high = fid_score_percentile(problems, weights, "fid_high")
    result_low = fid_score_percentile(problems, weights, "fid_low")

    assert isinstance(result_high, float), "Must return float; got " + repr(type(result_high))
    assert abs(result_high - 1.0) < 1e-9, f"fid_high (top) -> 1.0; got {result_high}"
    assert abs(result_low - 0.0) < 1e-9, f"fid_low (bottom) -> 0.0; got {result_low}"


def test_strictly_lower_not_gte() -> None:
    """Percentile uses STRICTLY LOWER count (not >=).

    Three fids: fid_a=1.0, fid_b=3.0, fid_c=3.0.
    Percentile of fid_b = 1 strictly-lower / 2 = 0.5.
    Wrong impl using >= would get 2/2=1.0 (tied fids counted).
    Kills impl with a >= or <= direction error.
    """
    problems = [
        _p("C", "fid_a", "LOW"),  # 1.0
        _p("C", "fid_b", "MED"),  # 3.0
        _p("C", "fid_c", "MED"),  # 3.0
    ]
    weights = {"LOW": 1.0, "MED": 3.0}
    result = fid_score_percentile(problems, weights, "fid_b")
    assert result is not None, "fid_b is present; must not return None"
    assert abs(result - 0.5) < 1e-9, f"1 strictly-lower / (3-1) = 0.5; got {result} (wrong >=: 1.0)"


def test_single_fid_returns_zero_not_none() -> None:
    """Single fid -> 0.0 (not None).

    Kills impl that returns None when there's only one fid (denominator 0 guard
    wrong — should be special-cased to 0.0 not None).
    """
    problems = [_p("C", "fid_x", "HIGH"), _p("C", "fid_x", "HIGH")]
    result = fid_score_percentile(problems, {"HIGH": 5.0}, "fid_x")
    assert result == 0.0, f"Single fid -> 0.0; got {result}"


def test_absent_fid_returns_none() -> None:
    """Absent finding_id -> None (not raise).

    Kills impl raising KeyError on absent fid.
    """
    problems = [_p("C", "fid_present", "HIGH")]
    result = fid_score_percentile(problems, {"HIGH": 5.0}, "fid_absent")
    assert result is None, f"Absent fid -> None; got {result}"


def test_empty_problems_returns_none() -> None:
    """Empty problems -> None (not raise)."""
    result = fid_score_percentile([], {"HIGH": 5.0}, "fid_x")
    assert result is None, f"Empty -> None; got {result}"
