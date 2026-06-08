"""Item 773: fid_severity_rank_interdecile_range() -- inter-decile range (p90-p10) per fid.

fid_severity_rank_interdecile_range(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_interdecile_range (item 772).
IDR = p90 - p10 per fid; all-same -> 0.0; empty -> {}; pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [0,1,2,3,4] -> IDR=3.2;
     class-outer gives 'A' wrong; IQR=2.0 wrong.
  2. All-same -> 0.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_interdecile_range


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_idr_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; IDR=3.2; class-outer wrong; IQR=2.0 wrong.

    fid f1: [INFO(0),LOW(1),MEDIUM(2),HIGH(3),CRITICAL(4)] -> p10=0.4, p90=3.6, IDR=3.2.
    """
    problems = [_p("f1", "INFO"), _p("f1", "LOW"), _p("f1", "MEDIUM"), _p("f1", "HIGH"), _p("f1", "CRITICAL")]
    result = fid_severity_rank_interdecile_range(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    expected = 3.2
    assert math.isclose(got, expected, abs_tol=1e-9), (
        f"[0,1,2,3,4] -> IDR={expected}; got {got}"
    )
    assert not math.isclose(got, 2.0, abs_tol=1e-6), "Must be IDR not IQR (2.0)"


def test_all_same_gives_zero() -> None:
    """All same -> IDR = 0.0."""
    problems = [_p("f2", "CRITICAL")] * 3
    result = fid_severity_rank_interdecile_range(problems)
    got = result.get("f2")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"All CRITICAL -> IDR=0.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_interdecile_range([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = [
        _p("fA", "INFO"), _p("fA", "LOW"), _p("fA", "MEDIUM"), _p("fA", "HIGH"), _p("fA", "CRITICAL"),  # IDR=3.2
        _p("fB", "HIGH"), _p("fB", "HIGH"), _p("fB", "HIGH"),  # all-same -> 0.0
    ]
    result = fid_severity_rank_interdecile_range(problems)
    assert math.isclose(result["fA"], 3.2, abs_tol=1e-9), f"fA -> IDR=3.2; got {result['fA']}"
    assert math.isclose(result["fB"], 0.0, abs_tol=1e-9), f"fB -> IDR=0.0; got {result['fB']}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f3", "LOW"), _p("f3", "HIGH"), _p("f3", "CRITICAL")]
    result = fid_severity_rank_interdecile_range(problems)
    assert isinstance(result["f3"], float), f"Must be float; got {type(result['f3'])}"
