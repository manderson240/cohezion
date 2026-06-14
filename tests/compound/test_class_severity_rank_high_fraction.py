"""Item 786: class_severity_rank_high_fraction() -- fraction of rank>=3 per class.

class_severity_rank_high_fraction(problems) -> dict[str, float].
Fraction of problems with severity rank >= 3 (HIGH or CRITICAL) per class.
count(rank >= 3) / n.  all-LOW/INFO -> 0.0.  all-CRITICAL -> 1.0.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: high_fraction != mean_rank and != count; class A: [INFO*3, HIGH*2]
     -> high_fraction=0.4; mean_rank=(0*3+3*2)/5=1.2 wrong; count=2 wrong.
  2. All low-severity -> 0.0.
  3. All CRITICAL -> 1.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_high_fraction


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_high_fraction_not_mean_not_count_primary_discriminator() -> None:
    """PRIMARY DISC.: high_fraction=0.4; mean_rank=1.2 wrong; count=2 wrong.

    class A: [INFO(0)*3, HIGH(3)*2] -> count(rank>=3)=2, n=5, fraction=0.4.
    mean_rank-impl: (0+0+0+3+3)/5=1.2 (wrong type/value).
    count-impl: 2 (wrong -- not normalized).
    """
    problems = [_p("A", "INFO")] * 3 + [_p("A", "HIGH")] * 2
    result = class_severity_rank_high_fraction(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 0.4, abs_tol=1e-9), f"[INFO*3,HIGH*2] -> high_fraction=0.4; got {got}"
    assert not math.isclose(got, 1.2, abs_tol=1e-6), "Must be fraction not mean_rank (1.2)"
    assert got != 2, "Must be fraction not count (2)"


def test_all_low_severity_gives_zero() -> None:
    """All INFO/LOW/MEDIUM -> high_fraction = 0.0."""
    problems = [_p("B", "INFO"), _p("B", "LOW"), _p("B", "MEDIUM")]
    result = class_severity_rank_high_fraction(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), f"All rank<3 -> 0.0; got {got}"


def test_all_critical_gives_one() -> None:
    """All CRITICAL -> high_fraction = 1.0."""
    problems = [_p("C", "CRITICAL")] * 4
    result = class_severity_rank_high_fraction(problems)
    got = result.get("C")
    assert got is not None and math.isclose(got, 1.0, abs_tol=1e-9), (
        f"All CRITICAL -> 1.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_high_fraction([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "HIGH"), _p("D", "INFO")]
    result = class_severity_rank_high_fraction(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
