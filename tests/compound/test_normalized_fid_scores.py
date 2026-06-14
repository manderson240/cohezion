"""Item 524: normalized_fid_scores() -- fid scores mapped to [0,1] (2026-06-08).

``normalized_fid_scores(problems, weights) -> dict[str, float]``:
Maps each fid's total weighted severity score to [0.0, 1.0] via min-max
normalization.  All-same scores -> every fid maps to 0.0.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns FID-keyed dict (not class-keyed).
     fid_a=1.0, fid_b=0.0 -- kills impl reusing normalized_class_scores on wrong axis.
  2. Min-max normalization: max-scoring fid maps to 1.0, min to 0.0.
     Kills impl using sum-normalization or raw scores.
  3. All-same scores -> all 0.0 (no ZeroDivisionError).
     Kills impl without spread==0 guard.
  4. Single fid -> {fid: 0.0}.
     Kills impl returning None or raising on single-element input.
  5. Empty -> {}.
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    normalized_fid_scores,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_keyed_dict_not_class_keyed() -> None:
    """PRIMARY DISC.: dict is keyed by fid, not class name.

    fid_high=HIGH(3.0) -> 1.0; fid_low=LOW(1.0) -> 0.0.
    Kills impl reusing normalized_class_scores on wrong axis.
    """
    problems = [
        _p("ClassA", "fid_high", "HIGH"),
        _p("ClassA", "fid_low", "LOW"),
    ]
    result = normalized_fid_scores(problems, {"HIGH": 3.0, "LOW": 1.0})
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "fid_high" in result, "Must be keyed by fid; got " + repr(list(result.keys()))
    assert "fid_low" in result
    assert "ClassA" not in result, "Must NOT be keyed by class name"
    assert result["fid_high"] == 1.0, "Max-scoring fid -> 1.0; got " + repr(result)
    assert result["fid_low"] == 0.0, "Min-scoring fid -> 0.0; got " + repr(result)


def test_min_max_normalization() -> None:
    """Max fid -> 1.0, min fid -> 0.0, mid fid -> correct fraction.

    fid_a=5.0, fid_b=3.0, fid_c=1.0 -> 1.0, 0.5, 0.0.
    Kills impl using sum-normalization.
    """
    problems = [
        _p("C", "fid_a", "HIGH"),  # 5.0
        _p("C", "fid_b", "MED"),  # 3.0
        _p("C", "fid_c", "LOW"),  # 1.0
    ]
    result = normalized_fid_scores(problems, {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0})
    assert result["fid_a"] == 1.0, "Max -> 1.0; got " + repr(result)
    assert result["fid_c"] == 0.0, "Min -> 0.0; got " + repr(result)
    assert abs(result["fid_b"] - 0.5) < 1e-9, "Mid -> 0.5; got " + repr(result)


def test_all_same_scores_maps_to_zero() -> None:
    """All fids with equal score -> all 0.0 (no ZeroDivisionError).

    Kills impl without spread == 0 guard.
    """
    problems = [
        _p("C", "fid_a", "HIGH"),
        _p("C", "fid_b", "HIGH"),
    ]
    result = normalized_fid_scores(problems, {"HIGH": 3.0})
    assert all(v == 0.0 for v in result.values()), "All-same -> all 0.0; got " + repr(result)


def test_single_fid_maps_to_zero() -> None:
    """Single fid -> {fid: 0.0} (not None, not raise).

    Kills impl that fails on 1-element input.
    """
    problems = [_p("C", "fid_only", "HIGH")]
    result = normalized_fid_scores(problems, {"HIGH": 5.0})
    assert result == {"fid_only": 0.0}, "Single fid -> 0.0; got " + repr(result)


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {}.

    Kills impl without empty guard.
    """
    result = normalized_fid_scores([], {"HIGH": 3.0})
    assert result == {}, "Empty -> {}; got " + repr(result)
