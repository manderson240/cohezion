"""Item 735: fid_severity_rank_kurtosis() -- excess kurtosis of severity ranks per fid.

fid_severity_rank_kurtosis(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_kurtosis (item 734).
n < 4 -> 0.0.  All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND platykurtic kurtosis value;
     fid 'f1': INFO×2+CRITICAL×2 -> excess_kurtosis=-6.0; class-outer wrong; skew=0 wrong.
  2. All-same -> 0.0.
  3. n < 4 per fid -> 0.0.
  4. Empty -> {}.
  5. Multiple fids independent.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_kurtosis


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_bimodal_kurtosis_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND kurtosis=-6.0 for bimodal [0,0,4,4].

    fid 'f1': INFO×2+CRITICAL×2 -> excess_kurtosis=-6.0.
    class-outer gives key='A' wrong; skew=0.0 wrong.
    """
    problems = [_p("f1", "INFO"), _p("f1", "INFO"), _p("f1", "CRITICAL"), _p("f1", "CRITICAL")]
    result = fid_severity_rank_kurtosis(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, -6.0, abs_tol=1e-9), f"[0,0,4,4] -> excess_kurtosis=-6.0; got {got}"


def test_all_same_gives_zero() -> None:
    """All-same severity -> 0.0."""
    problems = [_p("f2", "HIGH")] * 5
    result = fid_severity_rank_kurtosis(problems)
    got = result.get("f2")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All HIGH -> 0.0; got {got}"


def test_fewer_than_4_gives_zero() -> None:
    """n < 4 per fid -> 0.0."""
    result = fid_severity_rank_kurtosis([_p("f3", "HIGH"), _p("f3", "LOW"), _p("f3", "INFO")])
    got = result.get("f3")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"n=3 -> 0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_kurtosis([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids computed independently."""
    problems = [_p("fa", "INFO"), _p("fa", "INFO"), _p("fa", "CRITICAL"), _p("fa", "CRITICAL")] + [
        _p("fb", "CRITICAL")
    ] * 4
    result = fid_severity_rank_kurtosis(problems)
    assert math.isclose(result["fa"], -6.0, abs_tol=1e-9), f"fa bimodal -> -6.0; got {result['fa']}"
    assert math.isclose(result["fb"], 0.0, abs_tol=1e-9), f"fb all-same -> 0.0; got {result['fb']}"
