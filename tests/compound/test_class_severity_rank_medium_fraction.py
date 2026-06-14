"""Item 794: class_severity_rank_medium_fraction() -- fraction MEDIUM-only per class.

class_severity_rank_medium_fraction(problems) -> dict[str, float].
fraction = count(rank == 2) / n per class (MEDIUM=2 only; LOW=1 and HIGH=3 do NOT count).
All LOW/HIGH -> 0.0.  All MEDIUM -> 1.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: medium_fraction \!= low_fraction; [LOW(1)*3, MEDIUM(2)*2]
     -> medium_fraction=2/5=0.4; low_fraction-impl=3/5=0.6 wrong; info_frac=0.0 wrong.
  2. All LOW -> 0.0 (rank 1, not 2).
  3. All MEDIUM -> 1.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_medium_fraction


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_medium_not_low_fraction_primary_discriminator() -> None:
    """PRIMARY DISC.: medium_fraction=0.4; low_fraction=0.6 wrong; info_frac=0.0 wrong.

    class A: [LOW(1)*3, MEDIUM(2)*2].
    medium_fraction = 2/5 = 0.4.
    low_fraction-impl: count(rank<=1)=3/5=0.6 (wrong; LOW also counted).
    info_fraction-impl: count(rank==0)=0/5=0.0 (wrong; no INFO).
    """
    problems = [_p("A", "LOW")] * 3 + [_p("A", "MEDIUM")] * 2
    result = class_severity_rank_medium_fraction(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 0.4, abs_tol=1e-9), f"[LOW*3,MED*2] -> 0.4; got {got}"
    assert not math.isclose(got, 0.6, abs_tol=1e-6), "LOW must not count (0.6 wrong)"
    assert not math.isclose(got, 0.0, abs_tol=1e-6), "MEDIUM must count (0.0 wrong)"


def test_all_low_gives_zero() -> None:
    """All LOW -> medium_fraction=0.0."""
    problems = [_p("B", "LOW")] * 4
    result = class_severity_rank_medium_fraction(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), f"All LOW -> 0.0; got {got}"


def test_all_medium_gives_one() -> None:
    """All MEDIUM -> medium_fraction = 1.0."""
    problems = [_p("C", "MEDIUM")] * 3
    result = class_severity_rank_medium_fraction(problems)
    got = result.get("C")
    assert got is not None and math.isclose(got, 1.0, abs_tol=1e-9), f"All MEDIUM -> 1.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_medium_fraction([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "MEDIUM"), _p("D", "HIGH")]
    result = class_severity_rank_medium_fraction(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
