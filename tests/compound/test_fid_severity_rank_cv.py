"""Item 737: fid_severity_rank_cv() -- coefficient of variation of severity ranks per fid.

fid_severity_rank_cv(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_cv (item 736).
CV = sample_std / mean; mean=0 -> 0.0; n <= 1 -> 0.0.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND CV not std;
     fid 'f1': LOW(1)+HIGH(3) -> CV=sqrt(2)/2~0.707; class-outer wrong; std~1.414 wrong.
  2. mean=0 -> 0.0.
  3. n <= 1 -> 0.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_cv


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_cv_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND CV=sqrt(2)/2 for [1,3].

    fid 'f1': LOW(1)+HIGH(3) -> CV=sqrt(2)/2~0.707; class-outer gives key='A' wrong.
    """
    problems = [_p("f1", "LOW"), _p("f1", "HIGH")]
    result = fid_severity_rank_cv(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    expected = math.sqrt(2) / 2
    assert math.isclose(got, expected, abs_tol=1e-6), (
        f"[1,3] -> CV=sqrt(2)/2~{expected:.6f}; got {got}"
    )


def test_mean_zero_gives_zero() -> None:
    """All INFO (rank=0) per fid -> mean=0 -> CV=0.0."""
    problems = [_p("f2", "INFO"), _p("f2", "INFO")]
    result = fid_severity_rank_cv(problems)
    got = result.get("f2")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All INFO -> CV=0.0; got {got}"


def test_single_problem_gives_zero() -> None:
    """n <= 1 per fid -> 0.0."""
    result = fid_severity_rank_cv([_p("f3", "HIGH")])
    got = result.get("f3")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"n=1 -> 0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_cv([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f4", "LOW"), _p("f4", "HIGH")]
    result = fid_severity_rank_cv(problems)
    assert isinstance(result["f4"], float), f"Must be float; got {type(result['f4'])}"
