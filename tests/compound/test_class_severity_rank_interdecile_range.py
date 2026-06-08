"""Item 772: class_severity_rank_interdecile_range() -- inter-decile range (p90-p10) per class.

class_severity_rank_interdecile_range(problems) -> dict[str, float].
IDR = p90 - p10 using linear interpolation; all-same -> 0.0; empty -> {}; pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: IDR not IQR not std; class A: [0,1,2,3,4] -> p10=0.4, p90=3.6, IDR=3.2;
     IQR-impl gives 2.0 wrong (p75-p25=3.0-1.0); std-impl gives ~1.58 wrong.
  2. All-same -> 0.0.
  3. Symmetric [INFO,CRITICAL] -> p10=0.2, p90=3.8, IDR=3.6.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_interdecile_range


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_idr_not_iqr_not_std_primary_discriminator() -> None:
    """PRIMARY DISC.: IDR=3.2; IQR-impl gives 2.0 wrong; std-impl gives ~1.58 wrong.

    class A: [INFO(0),LOW(1),MEDIUM(2),HIGH(3),CRITICAL(4)].
    p10: i=0.4 -> 0.4; p90: i=3.6 -> 3.6; IDR=3.6-0.4=3.2.
    IQR: p75=3.0, p25=1.0, IQR=2.0 (wrong).
    """
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "MEDIUM"), _p("A", "HIGH"), _p("A", "CRITICAL")]
    result = class_severity_rank_interdecile_range(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    expected = 3.2
    assert math.isclose(got, expected, abs_tol=1e-9), (
        f"[0,1,2,3,4] -> IDR=3.2; got {got}"
    )
    assert not math.isclose(got, 2.0, abs_tol=1e-6), "Must be IDR not IQR (2.0 is IQR)"
    assert not math.isclose(got, 4.0, abs_tol=1e-6), "Must be IDR not full range (4.0)"


def test_all_same_gives_zero() -> None:
    """All same severity -> IDR = 0.0."""
    problems = [_p("B", "HIGH")] * 4
    result = class_severity_rank_interdecile_range(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"All HIGH -> IDR=0.0; got {got}"
    )


def test_two_values_symmetric() -> None:
    """[INFO(0),CRITICAL(4)] -> p10=0+0.1*4=0.4, p90=0+0.9*4=3.6, IDR=3.2."""
    problems = [_p("C", "INFO"), _p("C", "CRITICAL")]
    result = class_severity_rank_interdecile_range(problems)
    got = result.get("C")
    # p10: i=0.1*(2-1)=0.1; sorted=[0,4]; lo=0,hi=1,frac=0.1; p10=0+0.1*4=0.4
    # p90: i=0.9*(2-1)=0.9; lo=0,hi=1,frac=0.9; p90=0+0.9*4=3.6
    # IDR = 3.6 - 0.4 = 3.2
    expected = 3.2
    assert got is not None and math.isclose(got, expected, abs_tol=1e-9), (
        f"[INFO,CRITICAL] -> IDR=3.2; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_interdecile_range([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "INFO"), _p("D", "LOW"), _p("D", "CRITICAL")]
    result = class_severity_rank_interdecile_range(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
