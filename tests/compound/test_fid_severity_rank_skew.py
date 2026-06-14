"""Item 733: fid_severity_rank_skew() -- sample skewness of severity ranks per fid.

fid_severity_rank_skew(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_skew (item 732).
n < 3 -> 0.0.  All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND positive/negative skewness preserved;
     fid 'f1': INFO(0)*2+CRITICAL(4) -> g1=sqrt(3)~1.732; class-outer wrong; zero wrong.
  2. Negative skewness for left-skewed distribution.
  3. n < 3 per fid -> 0.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_skew


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_positive_skew_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND positive skewness for right-skewed ranks.

    fid 'f1': INFO(0)*2+CRITICAL(4) -> ranks [0,0,4]; g1=sqrt(3)~1.732.
    class-outer gives key='A' wrong; zero-impl gives 0.0 wrong.
    """
    problems = [_p("f1", "INFO"), _p("f1", "INFO"), _p("f1", "CRITICAL")]
    result = fid_severity_rank_skew(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert got > 0, f"Right-skewed [0,0,4] -> positive; got {got}"
    assert math.isclose(got, math.sqrt(3), abs_tol=1e-6), (
        f"[0,0,4] -> sqrt(3)~{math.sqrt(3):.6f}; got {got}"
    )


def test_negative_skew_left_skewed() -> None:
    """Left-skewed fid -> negative skewness.

    fid 'f2': CRITICAL(4)*2+INFO(0) -> ranks [0,4,4]; g1=-sqrt(3).
    """
    problems = [_p("f2", "CRITICAL"), _p("f2", "CRITICAL"), _p("f2", "INFO")]
    result = fid_severity_rank_skew(problems)
    got = result.get("f2")
    assert got is not None and got < 0, f"Left-skewed -> negative; got {got}"
    assert math.isclose(got, -math.sqrt(3), abs_tol=1e-6), (
        f"[0,4,4] -> -sqrt(3)~{-math.sqrt(3):.6f}; got {got}"
    )


def test_fewer_than_3_gives_zero() -> None:
    """n < 3 per fid -> 0.0."""
    result = fid_severity_rank_skew([_p("f3", "HIGH"), _p("f3", "LOW")])
    got = result.get("f3")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"n=2 -> 0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_skew([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f4", "INFO"), _p("f4", "INFO"), _p("f4", "CRITICAL")]
    result = fid_severity_rank_skew(problems)
    assert isinstance(result["f4"], float), f"Must be float; got {type(result['f4'])}"
