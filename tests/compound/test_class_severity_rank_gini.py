"""Item 738: class_severity_rank_gini() -- Gini coefficient of severity ranks per class.

class_severity_rank_gini(problems) -> dict[str, float].
Gini = sum_i_j |xi-xj| / (2*n^2*mean).  mean=0 -> 0.0.  n=1 -> 0.0.
Returns value in [0,1].  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: Gini not range; class A: INFO(0)+CRITICAL(4) -> mean=2, sum_|xi-xj|=8;
     Gini=8/(2*4*2)=0.5; range-impl gives 4 wrong; count-impl gives 2 wrong; mean-impl gives 2.0 wrong.
  2. All-same -> Gini=0.0 (perfect equality).
  3. mean=0 (all INFO) -> 0.0.
  4. n=1 -> 0.0.
  5. Empty -> {}.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_gini


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_gini_not_range_primary_discriminator() -> None:
    """PRIMARY DISC.: Gini=0.5 not range=4 for [0,4].

    class A: INFO(0)+CRITICAL(4) -> ranks [0,4]; n=2, mean=2;
    sum_|xi-xj| = |0-0|+|0-4|+|4-0|+|4-4| = 0+4+4+0 = 8;
    Gini = 8/(2*4*2) = 0.5.
    range-impl gives 4 wrong; count-impl gives 2 wrong.
    """
    problems = [_p("A", "INFO"), _p("A", "CRITICAL")]
    result = class_severity_rank_gini(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 0.5, abs_tol=1e-9), (
        f"[0,4] -> Gini=0.5; got {got} (range-impl=4 wrong, count-impl=2 wrong)"
    )
    assert isinstance(got, float), f"Must be float; got {type(got)}"


def test_all_same_gives_zero() -> None:
    """All-same severity -> Gini=0.0 (perfect equality)."""
    problems = [_p("B", "HIGH")] * 4
    result = class_severity_rank_gini(problems)
    got = result.get("B")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All HIGH -> Gini=0.0; got {got}"


def test_all_info_mean_zero_gives_zero() -> None:
    """All INFO (rank=0) -> mean=0 -> Gini=0.0."""
    problems = [_p("C", "INFO"), _p("C", "INFO"), _p("C", "INFO")]
    result = class_severity_rank_gini(problems)
    got = result.get("C")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All INFO -> Gini=0.0; got {got}"


def test_single_problem_gives_zero() -> None:
    """n=1 -> Gini=0.0."""
    result = class_severity_rank_gini([_p("D", "CRITICAL")])
    got = result.get("D")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"n=1 -> Gini=0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_gini([]) == {}
