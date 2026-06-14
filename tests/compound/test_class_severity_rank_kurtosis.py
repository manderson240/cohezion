"""Item 734: class_severity_rank_kurtosis() -- excess kurtosis of severity ranks per class.

class_severity_rank_kurtosis(problems) -> dict[str, float].
Fisher excess kurtosis: [(n*(n+1))/((n-1)*(n-2)*(n-3))]*sum(((x-mean)/s)^4)
                        - 3*(n-1)^2/((n-2)*(n-3)).
n < 4 -> 0.0.  All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: kurtosis not skewness; class A: [0,0,4,4] (symmetric bimodal)
     -> skew=0.0 (symmetric, skew-impl returns 0 wrong); kurtosis=-6.0.
  2. All-same -> 0.0.
  3. n < 4 -> 0.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_kurtosis


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_bimodal_negative_kurtosis_primary_discriminator() -> None:
    """PRIMARY DISC.: kurtosis \!= skewness for symmetric bimodal.

    class A: INFO(0)*2+CRITICAL(4)*2 -> ranks [0,0,4,4]; excess_kurtosis=-6.0.
    Skew-impl gives 0.0 wrong (symmetric -> skew=0); count-impl gives 4 wrong.
    """
    problems = [_p("A", "INFO"), _p("A", "INFO"), _p("A", "CRITICAL"), _p("A", "CRITICAL")]
    result = class_severity_rank_kurtosis(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    got = result["A"]
    # ranks=[0,0,4,4]: n=4, mean=2, s=4/sqrt(3)
    # sum(zi^4) = 4*(sqrt(3)/2)^4 = 4*(9/16)=9/4
    # kurtosis = (20/6)*(9/4) - 3*9/(2*1) = 7.5 - 13.5 = -6.0
    assert math.isclose(got, -6.0, abs_tol=1e-9), (
        f"[0,0,4,4] -> excess_kurtosis=-6.0 (platykurtic bimodal); got {got} "
        f"(skew-impl gives 0.0 wrong)"
    )
    assert isinstance(got, float), f"Must be float; got {type(got)}"


def test_all_same_gives_zero() -> None:
    """All-same severity -> 0.0 (zero variance)."""
    problems = [_p("B", "CRITICAL")] * 5
    result = class_severity_rank_kurtosis(problems)
    got = result.get("B")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All CRITICAL -> 0.0; got {got}"


def test_fewer_than_4_gives_zero() -> None:
    """n < 4 per class -> 0.0."""
    problems = [_p("C", "HIGH"), _p("C", "LOW"), _p("C", "INFO")]  # n=3
    result = class_severity_rank_kurtosis(problems)
    got = result.get("C")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"n=3 -> 0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_kurtosis([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "INFO"), _p("D", "INFO"), _p("D", "CRITICAL"), _p("D", "CRITICAL")]
    result = class_severity_rank_kurtosis(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
