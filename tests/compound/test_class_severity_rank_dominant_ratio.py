"""Item 751: class_severity_rank_dominant_ratio() -- fraction of problems at the majority rank per class.

class_severity_rank_dominant_ratio(problems) -> dict[str, float].
dominant_ratio = count(majority_rank) / n  where majority_rank = rank with highest count (ties -> min).
All-same -> 1.0.  n=1 -> 1.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: ratio not count AND not rank AND not HHI;
     class A: INFO(0)*2+CRITICAL(4) -> majority=0, ratio=2/3~0.667;
     count-impl gives 2 wrong; rank-impl gives 0.0 wrong; HHI-impl gives 0.52 wrong.
  2. All-same severity -> 1.0 (all problems at majority rank).
  3. n=1 -> 1.0 (single problem is trivially dominant).
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_dominant_ratio


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_ratio_not_count_not_rank_primary_discriminator() -> None:
    """PRIMARY DISC.: ratio=2/3, not count=2, not rank=0, not HHI=0.52.

    class A: INFO(0)*2+CRITICAL(4) -> majority_rank=0 (count 2>1); ratio=2/3~0.667.
    count-impl gives 2 wrong; rank-impl gives 0.0 wrong; HHI-impl gives 0.52 wrong.
    """
    problems = [_p("A", "INFO"), _p("A", "INFO"), _p("A", "CRITICAL")]
    result = class_severity_rank_dominant_ratio(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 2 / 3, abs_tol=1e-9), (
        f"INFO(0)*2+CRITICAL(4): majority=0, ratio=2/3~{2 / 3:.6f}; got {got}"
    )
    # Kill count-impl, rank-impl, HHI-impl
    assert not math.isclose(got, 2.0, abs_tol=1e-6), "Must be ratio not count"
    assert not math.isclose(got, 0.0, abs_tol=1e-6), "Must be ratio not rank-value"
    assert not math.isclose(got, 0.52, abs_tol=1e-2), "Must be ratio not HHI"


def test_all_same_gives_one() -> None:
    """All same severity -> dominant_ratio = 1.0 (every problem at the only rank)."""
    problems = [_p("B", "CRITICAL")] * 5
    result = class_severity_rank_dominant_ratio(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 1.0, abs_tol=1e-9), (
        f"All CRITICAL -> 1.0; got {got}"
    )


def test_n1_gives_one() -> None:
    """n=1 per class -> dominant_ratio = 1.0 (trivially dominant)."""
    result = class_severity_rank_dominant_ratio([_p("C", "HIGH")])
    got = result.get("C")
    assert got is not None and math.isclose(got, 1.0, abs_tol=1e-9), f"n=1 -> 1.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_dominant_ratio([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "INFO"), _p("D", "INFO"), _p("D", "CRITICAL")]
    result = class_severity_rank_dominant_ratio(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
