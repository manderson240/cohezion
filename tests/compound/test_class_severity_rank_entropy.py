"""Item 744: class_severity_rank_entropy() -- Shannon entropy of severity rank distribution per class.

class_severity_rank_entropy(problems) -> dict[str, float].
H = -sum(p_k * log2(p_k)) where p_k = count(rank=k)/n (over observed ranks only).
All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: entropy not count; class A: INFO(0)×2+HIGH(3)×2 -> H=1.0 bit;
     count-impl gives 4 wrong; mean-impl gives 1.5 wrong.
  2. All-same -> 0.0 (H=0 for single symbol).
  3. Uniform 5 ranks -> H=log2(5)~2.322.
  4. Empty -> {}.
  5. Multiple classes independent.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_entropy


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_entropy_not_count_primary_discriminator() -> None:
    """PRIMARY DISC.: H=1.0 for balanced [0,0,3,3]; count=4 wrong; mean=1.5 wrong.

    class A: INFO(0)×2+HIGH(3)×2 -> p(0)=0.5, p(3)=0.5; H=-2*(0.5*log2(0.5))=1.0 bit.
    """
    problems = [_p("A", "INFO"), _p("A", "INFO"), _p("A", "HIGH"), _p("A", "HIGH")]
    result = class_severity_rank_entropy(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 1.0, abs_tol=1e-9), (
        f"INFO×2+HIGH×2 -> H=1.0; got {got} (count=4 wrong, mean=1.5 wrong)"
    )
    assert isinstance(got, float), f"Must be float; got {type(got)}"


def test_all_same_gives_zero() -> None:
    """All-same severity -> H=0.0 (no disorder)."""
    problems = [_p("B", "CRITICAL")] * 5
    result = class_severity_rank_entropy(problems)
    got = result.get("B")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All CRITICAL -> H=0.0; got {got}"


def test_uniform_five_ranks_max_entropy() -> None:
    """One of each rank [0,1,2,3,4] -> H=log2(5)~2.322."""
    problems = [
        _p("C", "INFO"),
        _p("C", "LOW"),
        _p("C", "MEDIUM"),
        _p("C", "HIGH"),
        _p("C", "CRITICAL"),
    ]
    result = class_severity_rank_entropy(problems)
    got = result.get("C")
    assert math.isclose(got, math.log2(5), abs_tol=1e-9), (
        f"Uniform 5 -> H=log2(5)~{math.log2(5):.6f}; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_entropy([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class computed independently."""
    problems = (
        [_p("X", "INFO"), _p("X", "INFO"), _p("X", "HIGH"), _p("X", "HIGH")]  # H=1.0
        + [_p("Y", "MEDIUM")] * 4  # all-same -> H=0.0
    )
    result = class_severity_rank_entropy(problems)
    assert math.isclose(result["X"], 1.0, abs_tol=1e-9), f"X -> H=1.0; got {result['X']}"
    assert math.isclose(result["Y"], 0.0, abs_tol=1e-9), f"Y all-same -> H=0.0; got {result['Y']}"
