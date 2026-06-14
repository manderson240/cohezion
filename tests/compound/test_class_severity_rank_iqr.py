"""Item 730: class_severity_rank_iqr() -- IQR (Q3-Q1) of severity ranks per class.

class_severity_rank_iqr(problems) -> dict[str, float].
Exclusive IQR: lower_half=sorted[:n//2], upper_half=sorted[(n+1)//2:].
< 3 problems per class -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: IQR not range;
     class A: INFO(0)+LOW(1)+HIGH(3)+CRITICAL(4) -> IQR=3.0 (Q1=0.5 Q3=3.5);
     range-impl gives 4.0 wrong; std-impl gives ~1.58 wrong.
  2. < 3 problems per class -> 0.0.
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_iqr


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_iqr_not_range_primary_discriminator() -> None:
    """PRIMARY DISC.: IQR not range (range=4.0 is wrong here).

    class A: INFO(0)+LOW(1)+HIGH(3)+CRITICAL(4) -> sorted [0,1,3,4]
    Q1=median([0,1])=0.5; Q3=median([3,4])=3.5; IQR=3.0.
    range-impl: max-min=4-0=4.0 wrong; std-impl: ~1.58 wrong.
    """
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "HIGH"), _p("A", "CRITICAL")]
    result = class_severity_rank_iqr(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 3.0, abs_tol=1e-9), (
        f"INFO+LOW+HIGH+CRIT: IQR=3.0; got {got} (range-impl=4.0 wrong; std-impl=~1.58 wrong)"
    )


def test_fewer_than_3_gives_zero() -> None:
    """< 3 problems per class -> 0.0."""
    result = class_severity_rank_iqr([_p("B", "CRITICAL"), _p("B", "INFO")])
    got = result.get("B")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"2 problems -> 0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_iqr([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class computes independently."""
    # X: [0,1,3,4] -> IQR=3.0
    problems = [_p("X", "INFO"), _p("X", "LOW"), _p("X", "HIGH"), _p("X", "CRITICAL")]
    # Y: [2,2,2,2] -> IQR=0.0 (all same)
    problems += [_p("Y", "MEDIUM")] * 4
    result = class_severity_rank_iqr(problems)
    assert math.isclose(result["X"], 3.0, abs_tol=1e-9), f"X: IQR=3.0; got {result.get('X')}"
    assert math.isclose(result["Y"], 0.0, abs_tol=1e-9), (
        f"Y: all MEDIUM -> 0.0; got {result.get('Y')}"
    )


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("Z", "INFO"), _p("Z", "LOW"), _p("Z", "HIGH")]
    result = class_severity_rank_iqr(problems)
    assert isinstance(result["Z"], float), f"Must be float; got {type(result['Z'])}"
