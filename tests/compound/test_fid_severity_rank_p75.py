"""Item 764: fid_severity_rank_p75() -- 75th percentile severity rank per fid.

fid_severity_rank_p75(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_p75 (item 763).
p75 = linear interpolation 75th percentile per fid.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND p75 not median;
     fid f1: [0,1,2,3,4] -> p75=3.0; class-outer gives 'A' wrong; median=2.0 wrong.
  2. All-same -> float(rank).
  3. Two-element: [INFO(0),CRITICAL(4)] -> p75=3.0.
  4. Empty -> {}.
  5. Multiple fids independent.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_p75


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_p75_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND p75=3.0; median=2.0 wrong; class-outer wrong."""
    problems = [
        _p("f1", "INFO"),
        _p("f1", "LOW"),
        _p("f1", "MEDIUM"),
        _p("f1", "HIGH"),
        _p("f1", "CRITICAL"),
    ]
    result = fid_severity_rank_p75(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 3.0, abs_tol=1e-9), (
        f"[0,1,2,3,4] -> p75=3.0; got {repr(got)} (median=2.0 wrong)"
    )


def test_all_same_gives_that_rank_as_float() -> None:
    """All HIGH -> p75=3.0 (float)."""
    problems = [_p("f2", "HIGH")] * 4
    result = fid_severity_rank_p75(problems)
    got = result.get("f2")
    assert math.isclose(got, 3.0, abs_tol=1e-9), f"All HIGH -> p75=3.0; got {repr(got)}"


def test_two_element_interpolation() -> None:
    """[INFO(0),CRITICAL(4)] -> p75 = 0 + 0.75*(4-0) = 3.0."""
    problems = [_p("f3", "INFO"), _p("f3", "CRITICAL")]
    result = fid_severity_rank_p75(problems)
    got = result.get("f3")
    assert math.isclose(got, 3.0, abs_tol=1e-9), f"[0,4] -> p75=3.0; got {repr(got)}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_p75([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid computed independently."""
    problems = [
        _p("f4", "INFO"),
        _p("f4", "LOW"),
        _p("f4", "MEDIUM"),
        _p("f4", "HIGH"),
        _p("f4", "CRITICAL"),
    ] + [_p("f5", "MEDIUM")] * 3
    result = fid_severity_rank_p75(problems)
    assert math.isclose(result["f4"], 3.0, abs_tol=1e-9), (
        f"f4 [0,1,2,3,4] -> p75=3.0; got {repr(result.get('f4'))}"
    )
    assert math.isclose(result["f5"], 2.0, abs_tol=1e-9), (
        f"f5 all MEDIUM -> p75=2.0; got {repr(result.get('f5'))}"
    )
