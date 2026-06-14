"""Item 810: class_severity_rank_high_only_fraction() -- fraction rank==3 (HIGH only) per class.

class_severity_rank_high_only_fraction(problems) -> dict[str, float].
fraction = count(rank == 3) / n per class.
Distinct from class_severity_rank_high_fraction (item 786) which includes HIGH+CRITICAL (rank>=3).
CRITICAL (rank 4) NOT included.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: rank==3 only, not rank>=3; [HIGH*3,CRIT*2,MED*1] -> high_only_frac=3/6=0.5;
     high_fraction=5/6 wrong (includes CRIT); critical_frac=2/6 wrong.
  2. All CRITICAL -> 0.0 (not 1.0 as high_fraction would give).
  3. All HIGH -> 1.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_high_only_fraction


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_high_only_not_high_plus_critical_primary_discriminator() -> None:
    """PRIMARY DISC.: high_only=0.5 not high_fraction=5/6; [HIGH*3,CRIT*2,MED*1] -> 0.5."""
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "CRITICAL")] * 2 + [_p("A", "MEDIUM")] * 1
    result = class_severity_rank_high_only_fraction(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    expected = 3.0 / 6.0
    assert math.isclose(got, expected, abs_tol=1e-9), (
        f"[HIGH*3,CRIT*2,MED*1] -> high_only_frac=0.5; got {got}"
    )
    assert not math.isclose(got, 5.0 / 6.0, abs_tol=1e-6), (
        "Must be HIGH-only not HIGH+CRITICAL (5/6)"
    )


def test_all_critical_gives_zero() -> None:
    """All CRITICAL -> high_only_frac=0.0 (CRITICAL rank 4, not rank 3)."""
    problems = [_p("B", "CRITICAL")] * 4
    result = class_severity_rank_high_only_fraction(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"All CRITICAL -> 0.0; got {got}"
    )


def test_all_high_gives_one() -> None:
    """All HIGH -> fraction=1.0."""
    problems = [_p("C", "HIGH")] * 3
    result = class_severity_rank_high_only_fraction(problems)
    got = result.get("C")
    assert got is not None and math.isclose(got, 1.0, abs_tol=1e-9), f"All HIGH -> 1.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_high_only_fraction([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "HIGH"), _p("D", "CRITICAL")]
    result = class_severity_rank_high_only_fraction(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
