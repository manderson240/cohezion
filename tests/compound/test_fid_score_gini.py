"""Item 546: fid_score_gini() -- Gini coefficient of fid score distribution (2026-06-08).

``fid_score_gini(problems, weights) -> float``:
Returns G = sum_i sum_j |xi - xj| / (2 * n * sum(xi)) over per-fid totals.
0.0 for perfect equality, 0.0 for empty or single fid.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     One class, two fids fid_a=1.0 and fid_b=9.0:
     class_score_gini = 0.0 (single class guard), fid_score_gini = 0.4.
     Kills impl reusing class_score_gini on wrong axis (returns 0.0).
  2. 0.0 for equal fid totals (perfect equality).
     Kills impl returning non-zero for equal fids.
  3. Higher Gini for more unequal fids: [1,9] > [4,6].
     Kills fixed-value impl.
  4. Single fid -> 0.0 (no inequality possible).
     Kills impl without n<2 guard.
  5. Empty -> 0.0 (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_gini


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_gini_not_class_axis() -> None:
    """PRIMARY DISC.: keyed on FID axis, not class axis.

    All problems in ONE class, fid_a=1.0, fid_b=9.0:
      class_score_gini = 0.0 (single class, n<2 guard fires)
      fid_score_gini: n=2, sum=10, gini_sum=|1-1|+|1-9|+|9-1|+|9-9|=16
        G = 16 / (2 * 2 * 10) = 0.4
    Kills impl reusing class_score_gini (returns 0.0 for single class).
    """
    problems = [
        _p("SameClass", "fid_a", "LOW"),   # fid_a total = 1.0
        _p("SameClass", "fid_b", "HIGH"),  # fid_b total = 9.0
    ]
    weights = {"LOW": 1.0, "HIGH": 9.0}
    result = fid_score_gini(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # class_score_gini = 0.0 (1 class); fid_score_gini = 0.4 -- must not be 0.0
    assert abs(result - 0.4) < 1e-9, (
        f"Gini of fids [1,9] = 0.4; got {result} (0.0 = class axis is wrong)"
    )


def test_equal_fid_totals_return_zero() -> None:
    """Equal fid totals -> G=0.0 (perfect equality).

    Kills impl returning non-zero for equal fid totals.
    """
    problems = [
        _p("A", "fid_a", "S5"),  # fid_a = 5.0
        _p("B", "fid_b", "S5"),  # fid_b = 5.0
        _p("C", "fid_c", "S5"),  # fid_c = 5.0
    ]
    weights = {"S5": 5.0}
    result = fid_score_gini(problems, weights)
    assert result == 0.0, f"Equal fids [5,5,5] -> Gini=0.0; got {result}"


def test_higher_gini_for_more_unequal_fids() -> None:
    """More unequal fid distribution has higher Gini.

    [1, 9] -> G=0.4 > [4, 6] -> G=0.1.
    Kills impl returning a fixed or distribution-independent value.
    """
    problems_unequal = [_p("A", "fid_a", "LOW"), _p("B", "fid_b", "HIGH")]
    problems_tight = [_p("C", "fid_c", "MED_LO"), _p("D", "fid_d", "MED_HI")]
    w_unequal = {"LOW": 1.0, "HIGH": 9.0}
    w_tight = {"MED_LO": 4.0, "MED_HI": 6.0}
    gini_unequal = fid_score_gini(problems_unequal, w_unequal)
    gini_tight = fid_score_gini(problems_tight, w_tight)
    assert abs(gini_unequal - 0.4) < 1e-9, f"Gini([1,9])=0.4; got {gini_unequal}"
    assert abs(gini_tight - 0.1) < 1e-9, f"Gini([4,6])=0.1; got {gini_tight}"
    assert gini_unequal > gini_tight, "More unequal fids must have higher Gini"


def test_single_fid_returns_zero() -> None:
    """Single distinct fid -> Gini=0.0.

    Kills impl without n<2 guard.
    """
    problems = [
        _p("A", "only_fid", "HIGH"),
        _p("B", "only_fid", "LOW"),
    ]
    result = fid_score_gini(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == 0.0, f"Single fid -> Gini=0.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = fid_score_gini([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
