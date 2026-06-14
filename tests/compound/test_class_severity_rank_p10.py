"""Item 770: class_severity_rank_p10() -- 10th percentile severity rank per class.

class_severity_rank_p10(problems) -> dict[str, float].
Linear interpolation: i = 0.1*(n-1); lo=floor(i); hi=min(lo+1,n-1); frac=i-lo;
result = sorted[lo] + frac*(sorted[hi]-sorted[lo]).
All-same -> that rank as float.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: p10 not p25 not min; class A: [0,1,2,3,4] -> i=0.4, p10=0.4;
     p25-impl gives 1.0 wrong; min-impl gives 0.0 wrong.
  2. All-same -> same rank.
  3. Interpolation: [LOW(1),HIGH(3)] -> i=0.1, p10=1+0.1*(3-1)=1.2.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_p10


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_p10_not_p25_not_min_primary_discriminator() -> None:
    """PRIMARY DISC.: p10=0.4; p25-impl gives 1.0 wrong; min-impl gives 0.0 wrong.

    class A: [INFO(0),LOW(1),MEDIUM(2),HIGH(3),CRITICAL(4)] -> i=0.1*4=0.4,
    lo=0, hi=1, frac=0.4, p10=0+0.4*(1-0)=0.4.
    """
    problems = [
        _p("A", "INFO"),
        _p("A", "LOW"),
        _p("A", "MEDIUM"),
        _p("A", "HIGH"),
        _p("A", "CRITICAL"),
    ]
    result = class_severity_rank_p10(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    expected = 0.4
    assert math.isclose(got, expected, abs_tol=1e-9), f"[0,1,2,3,4] -> p10={expected}; got {got}"
    assert not math.isclose(got, 1.0, abs_tol=1e-6), "Must be p10 not p25 (1.0 is p25)"
    assert not math.isclose(got, 0.0, abs_tol=1e-6), "Must be p10 not min (0.0 is min)"


def test_all_same_gives_same_rank() -> None:
    """All same severity -> p10 equals that rank."""
    problems = [_p("B", "HIGH")] * 4
    result = class_severity_rank_p10(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 3.0, abs_tol=1e-9), (
        f"All HIGH(3) -> p10=3.0; got {got}"
    )


def test_interpolation_two_values() -> None:
    """[LOW(1),HIGH(3)] -> i=0.1*1=0.1; p10=1+0.1*(3-1)=1.2."""
    problems = [_p("C", "LOW"), _p("C", "HIGH")]
    result = class_severity_rank_p10(problems)
    got = result.get("C")
    expected = 1.2
    assert got is not None and math.isclose(got, expected, abs_tol=1e-9), (
        f"[LOW,HIGH] -> p10=1.2; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_p10([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "INFO"), _p("D", "CRITICAL")]
    result = class_severity_rank_p10(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
