"""Item 732: class_severity_rank_skew() -- sample skewness of severity ranks per class.

class_severity_rank_skew(problems) -> dict[str, float].
Fisher-Pearson sample skewness: n/((n-1)*(n-2)) * sum(((x-mean)/s)^3).
n < 3 -> 0.0.  All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: positive skewness for right-skewed distribution;
     class A: INFO(0)*2+CRITICAL(4) -> g1=sqrt(3)~1.732 (tail toward high ranks);
     zero-impl gives 0 wrong; std-impl gives ~1.886 wrong (std not skewness).
  2. Negative skewness for left-skewed distribution (sign check);
     class B: CRITICAL(4)*2+INFO(0) -> g1=-sqrt(3)~-1.732.
  3. n < 3 -> 0.0.
  4. All-same severity -> 0.0 (zero variance).
  5. Empty -> {}.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_skew


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_positive_skew_primary_discriminator() -> None:
    """PRIMARY DISC.: positive skewness for right-skewed ranks.

    class A: INFO(0)*2+CRITICAL(4) -> ranks [0,0,4]; g1=sqrt(3)~1.732.
    Zero-impl gives 0.0 wrong; count-impl gives 3 wrong.
    """
    problems = [_p("A", "INFO"), _p("A", "INFO"), _p("A", "CRITICAL")]
    result = class_severity_rank_skew(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    got = result["A"]
    # ranks=[0,0,4]: Fisher-Pearson skew = sqrt(3) approx 1.7320508
    assert got > 0, f"Right-skewed [0,0,4] -> positive skewness; got {got}"
    assert math.isclose(got, math.sqrt(3), abs_tol=1e-6), (
        f"[0,0,4] -> g1=sqrt(3)~{math.sqrt(3):.6f}; got {got}"
    )


def test_negative_skew_opposite_sign() -> None:
    """Left-skewed distribution -> negative skewness.

    class B: CRITICAL(4)*2+INFO(0) -> ranks [0,4,4]; g1=-sqrt(3)~-1.732.
    """
    problems = [_p("B", "CRITICAL"), _p("B", "CRITICAL"), _p("B", "INFO")]
    result = class_severity_rank_skew(problems)
    got = result.get("B")
    assert got is not None, "'B' must be present"
    assert got < 0, f"Left-skewed [0,4,4] -> negative skewness; got {got}"
    assert math.isclose(got, -math.sqrt(3), abs_tol=1e-6), (
        f"[0,4,4] -> g1=-sqrt(3)~{-math.sqrt(3):.6f}; got {got}"
    )


def test_fewer_than_3_gives_zero() -> None:
    """n < 3 per class -> 0.0."""
    result = class_severity_rank_skew([_p("C", "HIGH"), _p("C", "LOW")])
    got = result.get("C")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"n=2 -> 0.0; got {got}"


def test_all_same_severity_gives_zero() -> None:
    """All same severity -> 0.0 (zero variance, no skew)."""
    problems = [_p("D", "CRITICAL")] * 4
    result = class_severity_rank_skew(problems)
    got = result.get("D")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All CRITICAL -> 0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_skew([]) == {}
