"""Item 741: fid_severity_rank_mean_abs_dev() -- MAD of severity ranks per fid.

fid_severity_rank_mean_abs_dev(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_mean_abs_dev (item 740).
MAD = mean(|xi - mean|).  n=1 -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND MAD=2.0 for [0,4];
     fid 'f1': INFO+CRITICAL -> MAD=2.0; class-outer wrong; std~2.828 wrong.
  2. All-same -> 0.0.
  3. n=1 -> 0.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_mean_abs_dev


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_mad_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND MAD=2.0 for [0,4].

    fid 'f1': INFO+CRITICAL -> MAD=2.0; class-outer gives key='A' wrong.
    """
    problems = [_p("f1", "INFO"), _p("f1", "CRITICAL")]
    result = fid_severity_rank_mean_abs_dev(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 2.0, abs_tol=1e-9), f"[0,4] -> MAD=2.0; got {got}"


def test_all_same_gives_zero() -> None:
    """All-same severity -> MAD=0.0."""
    problems = [_p("f2", "MEDIUM")] * 3
    result = fid_severity_rank_mean_abs_dev(problems)
    got = result.get("f2")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All MEDIUM -> MAD=0.0; got {got}"


def test_single_problem_gives_zero() -> None:
    """n=1 -> MAD=0.0."""
    result = fid_severity_rank_mean_abs_dev([_p("f3", "HIGH")])
    got = result.get("f3")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"n=1 -> MAD=0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_mean_abs_dev([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f4", "INFO"), _p("f4", "CRITICAL")]
    result = fid_severity_rank_mean_abs_dev(problems)
    assert isinstance(result["f4"], float), f"Must be float; got {type(result['f4'])}"
