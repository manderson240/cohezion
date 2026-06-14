"""Item 766: fid_severity_rank_p25() -- 25th percentile of severity ranks per fid.

fid_severity_rank_p25(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_p25 (item 765).
25th percentile using linear interpolation per fid.
All-same -> that rank as float.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [INFO,LOW,MEDIUM,HIGH,CRITICAL]
     -> p25=1.0; class-outer gives 'A' wrong; median=2.0 wrong.
  2. All-same -> same rank as float.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_p25


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_p25_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; p25=1.0; class-outer wrong; median=2.0 wrong.

    fid f1: [INFO,LOW,MEDIUM,HIGH,CRITICAL] -> sorted=[0,1,2,3,4]; i=1; p25=1.0.
    """
    problems = [_p("f1", sev) for sev in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]
    result = fid_severity_rank_p25(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 1.0, abs_tol=1e-9), f"[0,1,2,3,4]: p25=1.0; got {got}"


def test_all_same_gives_same_rank() -> None:
    """All same -> p25 = that rank as float."""
    problems = [_p("f2", "MEDIUM")] * 3
    result = fid_severity_rank_p25(problems)
    got = result.get("f2")
    assert got is not None and math.isclose(got, 2.0, abs_tol=1e-9), (
        f"All MEDIUM(rank=2) -> p25=2.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_p25([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = (
        [_p("fA", sev) for sev in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]  # p25=1.0
        + [_p("fB", "HIGH")] * 4  # all-same HIGH(3) -> p25=3.0
    )
    result = fid_severity_rank_p25(problems)
    assert math.isclose(result["fA"], 1.0, abs_tol=1e-9), f"fA -> 1.0; got {result['fA']}"
    assert math.isclose(result["fB"], 3.0, abs_tol=1e-9), f"fB -> 3.0; got {result['fB']}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f3", sev) for sev in ["INFO", "HIGH"]]
    result = fid_severity_rank_p25(problems)
    assert isinstance(result["f3"], float), f"Must be float; got {type(result['f3'])}"
