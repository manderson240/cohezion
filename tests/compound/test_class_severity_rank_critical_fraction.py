"""Item 788: class_severity_rank_critical_fraction() -- fraction CRITICAL-only per class.

class_severity_rank_critical_fraction(problems) -> dict[str, float].
fraction = count(rank == 4) / n per class (CRITICAL=4 only; HIGH=3 does not count).
All HIGH -> 0.0.  All CRITICAL -> 1.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: critical_fraction \!= high_fraction; [HIGH(3)*3, CRITICAL(4)*2]
     -> critical=2/5=0.4; high_fraction-impl=1.0 wrong (HIGH rank>=3 also counts).
  2. All HIGH -> 0.0 (rank 3, not 4).
  3. All CRITICAL -> 1.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_critical_fraction


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_critical_not_high_fraction_primary_discriminator() -> None:
    """PRIMARY DISC.: critical_fraction=0.4; high_fraction-impl=1.0 wrong.

    class A: [HIGH(3)*3, CRITICAL(4)*2].
    critical_fraction = 2/5 = 0.4.
    high_fraction-impl: count(rank>=3)=5/5=1.0 (wrong; HIGH also counted).
    """
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "CRITICAL")] * 2
    result = class_severity_rank_critical_fraction(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 0.4, abs_tol=1e-9), f"[HIGH*3,CRIT*2] -> 0.4; got {got}"
    assert not math.isclose(got, 1.0, abs_tol=1e-6), "Must be critical only not high_fraction (1.0)"


def test_all_high_gives_zero() -> None:
    """All HIGH (rank=3) -> critical_fraction=0.0 (HIGH is not CRITICAL)."""
    problems = [_p("B", "HIGH")] * 4
    result = class_severity_rank_critical_fraction(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), f"All HIGH -> 0.0; got {got}"


def test_all_critical_gives_one() -> None:
    """All CRITICAL -> critical_fraction = 1.0."""
    problems = [_p("C", "CRITICAL")] * 3
    result = class_severity_rank_critical_fraction(problems)
    got = result.get("C")
    assert got is not None and math.isclose(got, 1.0, abs_tol=1e-9), (
        f"All CRITICAL -> 1.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_critical_fraction([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "CRITICAL"), _p("D", "HIGH")]
    result = class_severity_rank_critical_fraction(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
