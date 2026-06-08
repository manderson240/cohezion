"""Item 748: class_severity_rank_concentration() -- HHI of severity rank distribution per class.

class_severity_rank_concentration(problems) -> dict[str, float].
HHI = sum(p_k^2) where p_k = count(rank=k)/n.  [1/K,1] for K distinct ranks.
All-same -> 1.0 (monopoly).  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: HHI not entropy; class A: INFO(0)*3+HIGH(3)*2 -> p(0)=0.6, p(3)=0.4;
     HHI=0.36+0.16=0.52; entropy-impl gives H~0.971 wrong; count-impl gives 5 wrong.
  2. All-same -> HHI=1.0 (perfect concentration).
  3. Uniform 5 ranks -> HHI=0.2 (min concentration).
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_concentration


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_hhi_not_entropy_primary_discriminator() -> None:
    """PRIMARY DISC.: HHI=0.52 not entropy for INFO(0)*3+HIGH(3)*2.

    class A: p(0)=3/5=0.6, p(3)=2/5=0.4; HHI=0.36+0.16=0.52.
    entropy-impl gives -0.6*log2(0.6)-0.4*log2(0.4)~0.971 wrong.
    """
    problems = [_p("A", "INFO"), _p("A", "INFO"), _p("A", "INFO"), _p("A", "HIGH"), _p("A", "HIGH")]
    result = class_severity_rank_concentration(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 0.52, abs_tol=1e-9), (
        f"[0.6,0.4] -> HHI=0.52; got {got} (entropy~0.971 wrong)"
    )
    assert isinstance(got, float), f"Must be float; got {type(got)}"


def test_all_same_gives_one() -> None:
    """All-same severity -> HHI=1.0 (perfect concentration)."""
    problems = [_p("B", "CRITICAL")] * 5
    result = class_severity_rank_concentration(problems)
    got = result.get("B")
    assert math.isclose(got, 1.0, abs_tol=1e-9), f"All CRITICAL -> HHI=1.0; got {got}"


def test_uniform_five_ranks_min_concentration() -> None:
    """One of each rank [0,1,2,3,4] -> HHI=5*(0.2)^2=0.2 (min concentration)."""
    problems = [
        _p("C", "INFO"),
        _p("C", "LOW"),
        _p("C", "MEDIUM"),
        _p("C", "HIGH"),
        _p("C", "CRITICAL"),
    ]
    result = class_severity_rank_concentration(problems)
    got = result.get("C")
    assert math.isclose(got, 0.2, abs_tol=1e-9), f"Uniform -> HHI=0.2; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_concentration([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "INFO"), _p("D", "HIGH")]
    result = class_severity_rank_concentration(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
