"""Item 792: class_severity_rank_info_fraction() -- fraction INFO-only per class.

class_severity_rank_info_fraction(problems) -> dict[str, float].
fraction = count(rank == 0) / n per class (INFO=0 only; LOW=1 does NOT count).
All LOW -> 0.0.  All INFO -> 1.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: info_fraction \!= low_fraction; [INFO(0)*2, LOW(1)*3]
     -> info_fraction=2/5=0.4; low_fraction-impl=5/5=1.0 wrong (LOW rank<=1 counts).
  2. All LOW -> 0.0 (rank 1, not 0).
  3. All INFO -> 1.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_info_fraction


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_info_not_low_fraction_primary_discriminator() -> None:
    """PRIMARY DISC.: info_fraction=0.4; low_fraction-impl=1.0 wrong.

    class A: [INFO(0)*2, LOW(1)*3].
    info_fraction = 2/5 = 0.4 (only INFO=0 counts).
    low_fraction-impl: count(rank<=1)=5/5=1.0 (wrong; LOW also counted).
    """
    problems = [_p("A", "INFO")] * 2 + [_p("A", "LOW")] * 3
    result = class_severity_rank_info_fraction(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 0.4, abs_tol=1e-9), f"[INFO*2,LOW*3] -> 0.4; got {got}"
    assert not math.isclose(got, 1.0, abs_tol=1e-6), (
        "LOW must not count in info_fraction (1.0 wrong)"
    )


def test_all_low_gives_zero() -> None:
    """All LOW (rank=1) -> info_fraction=0.0 (LOW \!= INFO)."""
    problems = [_p("B", "LOW")] * 4
    result = class_severity_rank_info_fraction(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), f"All LOW -> 0.0; got {got}"


def test_all_info_gives_one() -> None:
    """All INFO -> info_fraction = 1.0."""
    problems = [_p("C", "INFO")] * 3
    result = class_severity_rank_info_fraction(problems)
    got = result.get("C")
    assert got is not None and math.isclose(got, 1.0, abs_tol=1e-9), f"All INFO -> 1.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_info_fraction([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "INFO"), _p("D", "MEDIUM")]
    result = class_severity_rank_info_fraction(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
