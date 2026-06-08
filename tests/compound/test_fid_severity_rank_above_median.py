"""Item 758: fid_severity_rank_above_median() -- fraction above median rank per fid.

fid_severity_rank_above_median(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_above_median (item 757).
fraction = count(rank > median) / n per fid.
All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND above-fraction not median value;
     fid f1: INFO(0)*2+CRITICAL(4) -> median=0, fraction=1/3; class-outer gives 'A' wrong;
     median-impl gives 0.0 wrong; count-impl gives 1 wrong.
  2. Symmetric [INFO,CRITICAL] -> fraction=0.5.
  3. All-same -> 0.0.
  4. Empty -> {}.
  5. Multiple fids independent.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_above_median


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_above_median_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND fraction=1/3; median=0.0 wrong; count=1 wrong.

    fid f1: INFO(0)*2+CRITICAL(4) -> median=0; count(>0)=1; fraction=1/3.
    """
    problems = [_p("f1", "INFO"), _p("f1", "INFO"), _p("f1", "CRITICAL")]
    result = fid_severity_rank_above_median(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class must NOT be key; got {list(result)}"
    got = result["f1"]
    expected = 1 / 3
    assert math.isclose(got, expected, abs_tol=1e-9), (
        f"INFO*2+CRITICAL -> fraction=1/3~{expected:.6f}; got {repr(got)}"
    )


def test_symmetric_two_gives_half() -> None:
    """INFO(0)+CRITICAL(4) per fid -> median=2.0; fraction=0.5."""
    problems = [_p("f2", "INFO"), _p("f2", "CRITICAL")]
    result = fid_severity_rank_above_median(problems)
    got = result.get("f2")
    assert math.isclose(got, 0.5, abs_tol=1e-9), f"INFO+CRITICAL: fraction=0.5; got {repr(got)}"


def test_all_same_gives_zero() -> None:
    """All-same -> fraction=0.0."""
    problems = [_p("f3", "MEDIUM")] * 4
    result = fid_severity_rank_above_median(problems)
    got = result.get("f3")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All MEDIUM -> 0.0; got {repr(got)}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_above_median([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid computed independently."""
    problems = (
        [_p("f4", "INFO"), _p("f4", "INFO"), _p("f4", "CRITICAL")]  # frac=1/3
        + [_p("f5", "HIGH")] * 3  # all-same -> 0.0
    )
    result = fid_severity_rank_above_median(problems)
    assert math.isclose(result["f4"], 1 / 3, abs_tol=1e-9), (
        f"f4 -> 1/3; got {repr(result.get('f4'))}"
    )
    assert math.isclose(result["f5"], 0.0, abs_tol=1e-9), (
        f"f5 all-same -> 0.0; got {repr(result.get('f5'))}"
    )
