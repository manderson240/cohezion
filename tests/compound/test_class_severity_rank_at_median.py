"""Item 761: class_severity_rank_at_median() -- fraction exactly at median rank per class.

class_severity_rank_at_median(problems) -> dict[str, float].
fraction = count(rank == median) / n per class.
All-same -> 1.0.  above + at + below == 1.0 (partition).  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: at-median NOT above or below; INFO(0)*2+CRITICAL(4)
     -> median=0, at-count=2, fraction=2/3; above-impl gives 1/3 wrong; below-impl gives 0.0 wrong.
  2. All-same -> 1.0 (all at median).
  3. Partition: above + at + below == 1.0 for any distribution.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import (
    Problem,
    class_severity_rank_at_median,
    class_severity_rank_above_median,
    class_severity_rank_below_median,
)


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_at_not_above_not_below_primary_discriminator() -> None:
    """PRIMARY DISC.: at=2/3; above=1/3 wrong; below=0.0 wrong.

    class A: INFO(0)*2+CRITICAL(4) -> sorted=[0,0,4], median=0; at-count=2, frac=2/3.
    """
    problems = [_p("A", "INFO"), _p("A", "INFO"), _p("A", "CRITICAL")]
    result = class_severity_rank_at_median(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 2 / 3, abs_tol=1e-9), (
        f"INFO*2+CRITICAL: median=0, at=2/3~{2 / 3:.6f}; got {got}"
    )
    assert not math.isclose(got, 1 / 3, abs_tol=1e-6), "Must be 'at' not 'above'"
    assert not math.isclose(got, 0.0, abs_tol=1e-6), "Must not be zero"


def test_all_same_gives_one() -> None:
    """All same -> at_median = 1.0 (all at the (only) rank = median)."""
    problems = [_p("B", "HIGH")] * 4
    result = class_severity_rank_at_median(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 1.0, abs_tol=1e-9), f"All HIGH -> 1.0; got {got}"


def test_partition_above_at_below_sum_to_one() -> None:
    """above + at + below == 1.0 (partition of all problems)."""
    problems = [
        _p("C", "INFO"),
        _p("C", "INFO"),
        _p("C", "MEDIUM"),
        _p("C", "CRITICAL"),
    ]
    above = class_severity_rank_above_median(problems)["C"]
    at = class_severity_rank_at_median(problems)["C"]
    below = class_severity_rank_below_median(problems)["C"]
    total = above + at + below
    assert math.isclose(total, 1.0, abs_tol=1e-9), (
        f"above({above}) + at({at}) + below({below}) = {total} != 1.0"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_at_median([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "INFO"), _p("D", "INFO"), _p("D", "CRITICAL")]
    result = class_severity_rank_at_median(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
