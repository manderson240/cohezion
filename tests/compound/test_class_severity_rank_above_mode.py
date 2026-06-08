"""Item 780: class_severity_rank_above_mode() -- fraction above modal rank per class.

class_severity_rank_above_mode(problems) -> dict[str, float].
Modal rank = most frequent rank; tie -> min rank.
fraction = count(rank > modal_rank) / n.
All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: above_mode \!= above_median; [INFO(0)*2, HIGH(3)*2, CRITICAL(4)]
     -> modal_rank=0 (min-tie), count(>0)=3/5=0.6;
     above-median-impl: median=3, count(>3)=1/5=0.2 wrong.
  2. Modal rank at top -> 0.0.
  3. All-same -> 0.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_above_mode


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_above_mode_not_above_median_primary_discriminator() -> None:
    """PRIMARY DISC.: above_mode=0.6; above_median=0.2 wrong.

    class A: [INFO(0)*2, HIGH(3)*2, CRITICAL(4)].
    Counts={0:2, 3:2, 4:1}. max_count=2, tied={0,3}, modal_rank=min=0.
    count(>0) = HIGH*2+CRITICAL*1 = 3. fraction = 3/5 = 0.6.
    above_median: sorted=[0,0,3,3,4], median=3, count(>3)=1/5=0.2 (wrong).
    """
    problems = [_p("A", "INFO")] * 2 + [_p("A", "HIGH")] * 2 + [_p("A", "CRITICAL")]
    result = class_severity_rank_above_mode(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 0.6, abs_tol=1e-9), (
        f"[INFO*2,HIGH*2,CRITICAL] -> above_mode=0.6; got {got}"
    )
    assert not math.isclose(got, 0.2, abs_tol=1e-6), "Must be above_mode not above_median (0.2)"


def test_modal_rank_at_top_gives_zero() -> None:
    """When mode is the highest rank, fraction above = 0.0."""
    problems = [_p("B", "CRITICAL")] * 3 + [_p("B", "INFO")] * 2
    result = class_severity_rank_above_mode(problems)
    got = result.get("B")
    # modal_rank=4 (CRITICAL dominates); count(>4)=0; fraction=0.0
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"CRITICAL*3+INFO*2 -> above_mode=0.0; got {got}"
    )


def test_all_same_gives_zero() -> None:
    """All same -> above_mode = 0.0."""
    problems = [_p("C", "HIGH")] * 4
    result = class_severity_rank_above_mode(problems)
    got = result.get("C")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"All HIGH -> above_mode=0.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_above_mode([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "INFO"), _p("D", "INFO"), _p("D", "CRITICAL")]
    result = class_severity_rank_above_mode(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
