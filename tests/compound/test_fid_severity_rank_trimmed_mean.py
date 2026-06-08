"""Item 743: fid_severity_rank_trimmed_mean() -- trimmed mean of severity ranks per fid.

fid_severity_rank_trimmed_mean(problems, trim_frac=0.1) -> dict[str, float].
Fid-axis complement of class_severity_rank_trimmed_mean (item 742).
n <= 2 -> plain mean.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND trimmed\!=plain;
     fid 'f1': [0,0,0,4,4], trim_frac=0.2 -> 4/3~1.333; class-outer wrong; plain=1.6 wrong.
  2. n <= 2 -> plain mean.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_trimmed_mean


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_trimmed_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND trimmed\!=plain.

    fid 'f1': [0,0,0,4,4], trim_frac=0.2 -> 4/3; class-outer wrong; plain=1.6 wrong.
    """
    problems = [
        _p("f1", "INFO"),
        _p("f1", "INFO"),
        _p("f1", "INFO"),
        _p("f1", "CRITICAL"),
        _p("f1", "CRITICAL"),
    ]
    result = fid_severity_rank_trimmed_mean(problems, trim_frac=0.2)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 4 / 3, abs_tol=1e-9), f"[0,0,0,4,4] trim=0.2 -> 4/3; got {got}"


def test_small_n_uses_plain_mean() -> None:
    """n <= 2 -> plain mean."""
    result = fid_severity_rank_trimmed_mean([_p("f2", "INFO"), _p("f2", "CRITICAL")], trim_frac=0.2)
    got = result.get("f2")
    assert math.isclose(got, 2.0, abs_tol=1e-9), f"n=2 -> plain mean=2.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_trimmed_mean([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids computed independently."""
    problems = [
        _p("fa", "INFO"),
        _p("fa", "INFO"),
        _p("fa", "INFO"),
        _p("fa", "CRITICAL"),
        _p("fa", "CRITICAL"),
    ] + [_p("fb", "MEDIUM")] * 5
    result = fid_severity_rank_trimmed_mean(problems, trim_frac=0.2)
    assert math.isclose(result["fa"], 4 / 3, abs_tol=1e-9), f"fa -> 4/3; got {result['fa']}"
    assert math.isclose(result["fb"], 2.0, abs_tol=1e-9), (
        f"fb all-MEDIUM -> 2.0; got {result['fb']}"
    )


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f3", "LOW"), _p("f3", "HIGH"), _p("f3", "CRITICAL")]
    result = fid_severity_rank_trimmed_mean(problems, trim_frac=0.1)
    assert isinstance(result["f3"], float), f"Must be float; got {type(result['f3'])}"
