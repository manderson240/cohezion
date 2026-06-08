"""Item 771: fid_severity_rank_p10() -- 10th percentile severity rank per fid.

fid_severity_rank_p10(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_p10 (item 770).
Linear interpolation: i=0.1*(n-1); lo=floor(i); hi=min(lo+1,n-1);
result = sorted[lo] + frac*(sorted[hi]-sorted[lo]).
All-same -> that rank.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [0,1,2,3,4] -> p10=0.4;
     class-outer gives 'A' wrong; p25=1.0 wrong; min=0.0 wrong.
  2. All-same -> same rank.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_p10


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_p10_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; p10=0.4; class-outer wrong; p25=1.0 wrong.

    fid f1: [INFO(0),LOW(1),MEDIUM(2),HIGH(3),CRITICAL(4)] -> p10=0.4.
    """
    problems = [_p("f1", "INFO"), _p("f1", "LOW"), _p("f1", "MEDIUM"), _p("f1", "HIGH"), _p("f1", "CRITICAL")]
    result = fid_severity_rank_p10(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    expected = 0.4
    assert math.isclose(got, expected, abs_tol=1e-9), (
        f"[0,1,2,3,4] -> p10={expected}; got {got}"
    )
    assert not math.isclose(got, 1.0, abs_tol=1e-6), "Must be p10 not p25 (1.0)"


def test_all_same_gives_same_rank() -> None:
    """All same -> p10 = that rank."""
    problems = [_p("f2", "CRITICAL")] * 3
    result = fid_severity_rank_p10(problems)
    got = result.get("f2")
    assert got is not None and math.isclose(got, 4.0, abs_tol=1e-9), (
        f"All CRITICAL(4) -> p10=4.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_p10([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = [
        _p("fA", "INFO"), _p("fA", "LOW"), _p("fA", "MEDIUM"), _p("fA", "HIGH"), _p("fA", "CRITICAL"),  # 0.4
        _p("fB", "HIGH"), _p("fB", "HIGH"), _p("fB", "HIGH"),  # all-same -> 3.0
    ]
    result = fid_severity_rank_p10(problems)
    assert math.isclose(result["fA"], 0.4, abs_tol=1e-9), f"fA -> 0.4; got {result['fA']}"
    assert math.isclose(result["fB"], 3.0, abs_tol=1e-9), f"fB -> 3.0; got {result['fB']}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f3", "LOW"), _p("f3", "HIGH")]
    result = fid_severity_rank_p10(problems)
    assert isinstance(result["f3"], float), f"Must be float; got {type(result['f3'])}"
