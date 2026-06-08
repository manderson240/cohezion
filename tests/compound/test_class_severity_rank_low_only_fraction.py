"""Item 808: class_severity_rank_low_only_fraction() -- fraction rank==1 (LOW only) per class.

class_severity_rank_low_only_fraction(problems) -> dict[str, float].
fraction = count(rank == 1) / n per class.
Distinct from class_severity_rank_low_fraction (item 790) which includes INFO+LOW (rank<=1).
INFO (rank 0) NOT included.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: rank==1 only, not rank<=1; [LOW*3,INFO*2,MED*1] -> low_only_frac=3/6=0.5;
     low_fraction=5/6 wrong (includes INFO); info_frac=2/6 wrong.
  2. All INFO -> 0.0 (not 1.0 as low_fraction would give).
  3. All LOW -> 1.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_low_only_fraction


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_low_only_not_low_plus_info_primary_discriminator() -> None:
    """PRIMARY DISC.: low_only=0.5 not low_fraction=5/6; [LOW*3,INFO*2,MED*1] -> 0.5."""
    problems = [_p("A", "LOW")] * 3 + [_p("A", "INFO")] * 2 + [_p("A", "MEDIUM")] * 1
    result = class_severity_rank_low_only_fraction(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    expected = 3.0 / 6.0
    assert math.isclose(got, expected, abs_tol=1e-9), (
        f"[LOW*3,INFO*2,MED*1] -> low_only_frac=0.5; got {got}"
    )
    assert not math.isclose(got, 5.0 / 6.0, abs_tol=1e-6), "Must be LOW-only not INFO+LOW (5/6)"


def test_all_info_gives_zero() -> None:
    """All INFO -> low_only_frac=0.0 (INFO rank 0, not rank 1)."""
    problems = [_p("B", "INFO")] * 4
    result = class_severity_rank_low_only_fraction(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"All INFO -> 0.0; got {got}"
    )


def test_all_low_gives_one() -> None:
    """All LOW -> fraction=1.0."""
    problems = [_p("C", "LOW")] * 3
    result = class_severity_rank_low_only_fraction(problems)
    got = result.get("C")
    assert got is not None and math.isclose(got, 1.0, abs_tol=1e-9), (
        f"All LOW -> 1.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_low_only_fraction([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "LOW"), _p("D", "HIGH")]
    result = class_severity_rank_low_only_fraction(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
