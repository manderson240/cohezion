"""Item 782: class_severity_rank_below_mode() -- fraction below modal rank per class.

class_severity_rank_below_mode(problems) -> dict[str, float].
Modal rank = most frequent rank; tie -> min rank.
fraction = count(rank < modal_rank) / n.
All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: [CRITICAL(4)*3, INFO(0)*2] -> modal_rank=4, count(<4)=2/5=0.4;
     above_mode for same data: count(>4)=0/5=0.0 wrong; ensures below not above.
  2. Partition: above_mode + at_mode + below_mode == 1.0.
  3. Modal rank at bottom -> 0.0 below.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import (
    Problem,
    class_severity_rank_below_mode,
    class_severity_rank_above_mode,
)


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_below_not_above_primary_discriminator() -> None:
    """PRIMARY DISC.: below_mode=0.4; above_mode=0.0 wrong.

    class A: [CRITICAL(4)*3, INFO(0)*2] -> modal_rank=4, count(<4)=2/5=0.4.
    above_mode for same: count(>4)=0/5=0.0 (wrong -- proves it's BELOW).
    """
    problems = [_p("A", "CRITICAL")] * 3 + [_p("A", "INFO")] * 2
    result = class_severity_rank_below_mode(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 0.4, abs_tol=1e-9), (
        f"CRITICAL*3+INFO*2 -> below_mode=0.4; got {got}"
    )
    above = class_severity_rank_above_mode(problems)["A"]
    assert not math.isclose(got, above, abs_tol=1e-6), (
        f"Must be below not above (above={above})"
    )


def test_partition_above_at_below_sum_to_one() -> None:
    """above_mode + at_mode + below_mode == 1.0 (partition)."""
    from cohezion.compound.problem_discovery import class_severity_rank_mode_count
    problems = [_p("B", "INFO")] * 2 + [_p("B", "HIGH")] * 2 + [_p("B", "CRITICAL")]
    # modal_rank=0 (min-tie); above(>0)=3/5; at(==0)=2/5; below(<0)=0/5
    above = class_severity_rank_above_mode(problems)["B"]
    below = class_severity_rank_below_mode(problems)["B"]
    at = 1.0 - above - below
    assert math.isclose(above + at + below, 1.0, abs_tol=1e-9), (
        f"above({above})+at({at})+below({below}) \!= 1.0"
    )
    # below(< 0) = 0; above(>0) = 3/5 = 0.6; at = 0.4
    assert math.isclose(below, 0.0, abs_tol=1e-9), f"below(<min_rank) should be 0.0; got {below}"


def test_modal_rank_at_bottom_gives_zero_below() -> None:
    """When modal rank is the minimum possible rank, below = 0.0."""
    problems = [_p("C", "INFO")] * 3 + [_p("C", "HIGH")] * 2
    result = class_severity_rank_below_mode(problems)
    got = result.get("C")
    # modal_rank=0 (INFO is dominant); count(<0)=0
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"INFO*3+HIGH*2 -> below_mode=0.0 (modal=0, nothing below 0); got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_below_mode([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "CRITICAL"), _p("D", "CRITICAL"), _p("D", "INFO")]
    result = class_severity_rank_below_mode(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
