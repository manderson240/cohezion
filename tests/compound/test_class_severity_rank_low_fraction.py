"""Item 790: class_severity_rank_low_fraction() -- fraction rank<=1 (INFO/LOW) per class.

class_severity_rank_low_fraction(problems) -> dict[str, float].
fraction = count(rank <= 1) / n per class (INFO=0, LOW=1 count; MEDIUM=2 does NOT).
All HIGH/CRITICAL -> 0.0.  All INFO -> 1.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: low_fraction != 1-high_fraction; class A: [INFO*2,LOW*1,MEDIUM*2]
     -> low_fraction=3/5=0.6; 1-high_fraction=1.0-0.0=1.0 wrong (MEDIUM not >= 3);
     high_fraction-impl=0.0 wrong.
  2. MEDIUM (rank=2) does not count as low.
  3. All INFO -> 1.0; all CRITICAL -> 0.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_low_fraction


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_low_fraction_not_complement_of_high_primary_discriminator() -> None:
    """PRIMARY DISC.: low_fraction=0.6; 1-high_fraction=1.0 wrong; high_frac=0.0 wrong.

    class A: [INFO(0)*2, LOW(1)*1, MEDIUM(2)*2].
    low_fraction = 3/5 = 0.6 (INFO and LOW count).
    1-high_fraction: high_fraction=0 (no rank>=3), so 1-0=1.0 (wrong; MEDIUM not low).
    """
    problems = [_p("A", "INFO")] * 2 + [_p("A", "LOW")] + [_p("A", "MEDIUM")] * 2
    result = class_severity_rank_low_fraction(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 0.6, abs_tol=1e-9), f"[INFO*2,LOW*1,MED*2] -> 0.6; got {got}"
    assert not math.isclose(got, 1.0, abs_tol=1e-6), "Must not include MEDIUM (1.0 wrong)"
    assert not math.isclose(got, 0.0, abs_tol=1e-6), "Must count INFO and LOW (0.0 wrong)"


def test_medium_does_not_count_as_low() -> None:
    """MEDIUM (rank=2) is strictly above threshold rank=1; not counted."""
    problems = [_p("B", "MEDIUM")] * 3 + [_p("B", "LOW")] * 1
    result = class_severity_rank_low_fraction(problems)
    got = result["B"]
    # Only LOW counts: 1/4 = 0.25; if MEDIUM counted: 4/4=1.0 wrong
    assert math.isclose(got, 0.25, abs_tol=1e-9), f"[MED*3,LOW*1] -> 0.25; got {got}"
    assert not math.isclose(got, 1.0, abs_tol=1e-6), "MEDIUM must not count as low"


def test_all_info_gives_one_all_critical_gives_zero() -> None:
    """All INFO -> 1.0; all CRITICAL -> 0.0."""
    problems = [_p("C", "INFO")] * 3 + [_p("D", "CRITICAL")] * 2
    result = class_severity_rank_low_fraction(problems)
    assert math.isclose(result["C"], 1.0, abs_tol=1e-9), f"All INFO -> 1.0; got {result['C']}"
    assert math.isclose(result["D"], 0.0, abs_tol=1e-9), f"All CRITICAL -> 0.0; got {result['D']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_low_fraction([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("E", "INFO"), _p("E", "HIGH")]
    result = class_severity_rank_low_fraction(problems)
    assert isinstance(result["E"], float), f"Must be float; got {type(result['E'])}"
