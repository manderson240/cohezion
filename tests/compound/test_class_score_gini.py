"""Item 545: class_score_gini() -- Gini coefficient of class score distribution (2026-06-08).

``class_score_gini(problems, weights) -> float``:
Returns G = sum_i sum_j |xi - xj| / (2 * n * sum(xi))
0.0 for perfect equality, 0.0 for empty or single class.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns GINI [0-1], not CV.
     For [1.0, 9.0]: Gini=0.4, CV=0.8.  Distinct from all other stats.
     Kills impl reusing class_score_cv (returns 0.8, not 0.4).
  2. 0.0 for perfectly uniform scores (perfect equality -> G=0).
     Kills impl returning non-zero for equal classes.
  3. Higher Gini for more unequal data vs. clustered data.
     [1, 9] -> 0.4 > [4, 6] -> 0.1 (kills fixed-value impl).
  4. Single class -> 0.0 (single class, no inequality possible).
     Kills impl without n<2 guard.
  5. Empty -> 0.0 (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_gini


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_gini_not_cv() -> None:
    """PRIMARY DISC.: returns Gini coefficient, not CV.

    Two classes A=1.0, B=9.0:
      n=2, sum=10.0, gini_sum = |1-1|+|1-9|+|9-1|+|9-9| = 16
      G = 16 / (2 * 2 * 10) = 0.4
      CV = std_dev/mean = 4.0/5.0 = 0.8
    Kills impl reusing class_score_cv (returns 0.8, not 0.4).
    """
    problems = [
        _p("A", "f1", "LOW"),  # class_total A = 1.0
        _p("B", "f2", "HIGH"),  # class_total B = 9.0
    ]
    weights = {"LOW": 1.0, "HIGH": 9.0}
    result = class_score_gini(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # Gini = 0.4; CV = 0.8 -- must not be 0.8
    assert abs(result - 0.4) < 1e-9, (
        f"Gini of [1,9] = 0.4; got {result} (0.8 = CV is wrong, not Gini)"
    )


def test_uniform_scores_return_zero() -> None:
    """Perfectly equal class totals -> G=0 (perfect equality).

    Kills impl returning non-zero for equal classes.
    """
    problems = [
        _p("A", "f1", "S5"),  # 5.0
        _p("B", "f2", "S5"),  # 5.0
        _p("C", "f3", "S5"),  # 5.0
    ]
    weights = {"S5": 5.0}
    result = class_score_gini(problems, weights)
    assert result == 0.0, f"Uniform [5,5,5] -> Gini=0.0; got {result}"


def test_higher_gini_for_more_unequal_data() -> None:
    """More unequal distribution has higher Gini.

    [1, 9] -> G=0.4 > [4, 6] -> G=0.1
    Kills impl returning a fixed or mean-independent value.
    """
    problems_unequal = [_p("A", "f1", "LOW"), _p("B", "f2", "HIGH")]
    problems_tight = [_p("C", "f3", "MED_LO"), _p("D", "f4", "MED_HI")]
    w_unequal = {"LOW": 1.0, "HIGH": 9.0}
    w_tight = {"MED_LO": 4.0, "MED_HI": 6.0}
    gini_unequal = class_score_gini(problems_unequal, w_unequal)
    gini_tight = class_score_gini(problems_tight, w_tight)
    # Gini([1,9]) = (0+8+8+0)/(2*2*10) = 16/40 = 0.4
    # Gini([4,6]) = (0+2+2+0)/(2*2*10) = 4/40 = 0.1
    assert abs(gini_unequal - 0.4) < 1e-9, f"Gini of [1,9] = 0.4; got {gini_unequal}"
    assert abs(gini_tight - 0.1) < 1e-9, f"Gini of [4,6] = 0.1; got {gini_tight}"
    assert gini_unequal > gini_tight, "More unequal data must have higher Gini"


def test_single_class_returns_zero() -> None:
    """Single class -> Gini=0.0 (no inequality possible between one element).

    Kills impl without n<2 guard.
    """
    problems = [
        _p("OnlyClass", "f1", "HIGH"),
        _p("OnlyClass", "f2", "LOW"),
    ]
    result = class_score_gini(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == 0.0, f"Single class -> Gini=0.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = class_score_gini([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
