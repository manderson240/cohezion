"""Item 739: fid_severity_rank_gini() -- Gini coefficient of severity ranks per fid.

fid_severity_rank_gini(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_gini (item 738).
Gini = sum_i_j |xi-xj| / (2*n^2*mean).  mean=0 -> 0.0.  n=1 -> 0.0.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND Gini=0.5 for [0,4];
     fid 'f1': INFO+CRITICAL -> Gini=0.5; class-outer wrong; range=4 wrong.
  2. All-same -> Gini=0.0.
  3. mean=0 -> 0.0.
  4. Empty -> {}.
  5. Multiple fids independent.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_gini


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_gini_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND Gini=0.5 for [0,4].

    fid 'f1': INFO+CRITICAL -> Gini=0.5; class-outer gives key='A' wrong.
    """
    problems = [_p("f1", "INFO"), _p("f1", "CRITICAL")]
    result = fid_severity_rank_gini(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 0.5, abs_tol=1e-9), f"[0,4] -> Gini=0.5; got {got}"


def test_all_same_gives_zero() -> None:
    """All-same severity -> Gini=0.0."""
    problems = [_p("f2", "CRITICAL")] * 3
    result = fid_severity_rank_gini(problems)
    got = result.get("f2")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All CRITICAL -> Gini=0.0; got {got}"


def test_all_info_mean_zero_gives_zero() -> None:
    """All INFO -> mean=0 -> Gini=0.0."""
    problems = [_p("f3", "INFO"), _p("f3", "INFO")]
    result = fid_severity_rank_gini(problems)
    got = result.get("f3")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All INFO -> Gini=0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_gini([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids computed independently."""
    problems = (
        [_p("fa", "INFO"), _p("fa", "CRITICAL")]  # fa -> 0.5
        + [_p("fb", "HIGH"), _p("fb", "HIGH")]  # fb all-same -> 0.0
    )
    result = fid_severity_rank_gini(problems)
    assert math.isclose(result["fa"], 0.5, abs_tol=1e-9), f"fa [0,4] -> 0.5; got {result['fa']}"
    assert math.isclose(result["fb"], 0.0, abs_tol=1e-9), f"fb all-same -> 0.0; got {result['fb']}"
