"""Item 794: class_severity_rank_fraction_below() -- fraction strictly below threshold per class.

class_severity_rank_fraction_below(problems, threshold: int) -> dict[str, float].
fraction = count(rank < threshold) / n per class.
Complement of fraction_at_or_above: both sum to 1.0.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: below not at-or-above; [CRIT(4)*3,HIGH(3)*2] fraction_below(4)=0.4;
     fraction_at_or_above(4)=0.6 wrong; partition: below(4)+at_or_above(4)=1.0.
  2. Threshold at or below minimum -> 0.0.
  3. Empty -> {}.
  4. Return type is float.
  5. Partition: fraction_below + fraction_at_or_above == 1.0.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import (
    Problem,
    class_severity_rank_fraction_below,
    class_severity_rank_fraction_at_or_above,
)


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_below_not_at_or_above_primary_discriminator() -> None:
    """PRIMARY DISC.: fraction_below(4)=0.4; fraction_at_or_above(4)=0.6 wrong.

    class A: [CRITICAL(4)*3, HIGH(3)*2].
    count(rank < 4) = 2 (HIGH); fraction = 2/5 = 0.4.
    fraction_at_or_above(4) = 3/5 = 0.6 (wrong -- complement).
    """
    problems = [_p("A", "CRITICAL")] * 3 + [_p("A", "HIGH")] * 2
    result = class_severity_rank_fraction_below(problems, 4)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 0.4, abs_tol=1e-9), (
        f"fraction_below(4) = 0.4; got {got}"
    )
    assert not math.isclose(got, 0.6, abs_tol=1e-6), "Must be below not at-or-above (0.6)"


def test_partition_below_plus_at_or_above_is_one() -> None:
    """fraction_below + fraction_at_or_above == 1.0 for any threshold."""
    problems = [_p("B", "CRITICAL")] * 3 + [_p("B", "HIGH")] * 2
    below = class_severity_rank_fraction_below(problems, 4)["B"]
    at_or_above = class_severity_rank_fraction_at_or_above(problems, 4)["B"]
    assert math.isclose(below + at_or_above, 1.0, abs_tol=1e-9), (
        f"below({below}) + at_or_above({at_or_above}) != 1.0"
    )


def test_threshold_at_or_below_minimum_gives_zero() -> None:
    """Threshold at or below all ranks -> fraction_below = 0.0."""
    problems = [_p("C", "HIGH")] * 3  # rank=3
    result = class_severity_rank_fraction_below(problems, 3)  # no rank < 3
    got = result.get("C")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"All HIGH(3) below threshold=3 -> 0.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_fraction_below([], 3) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "HIGH"), _p("D", "INFO")]
    result = class_severity_rank_fraction_below(problems, 3)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
