"""Item 731: fid_severity_rank_iqr() -- IQR (Q3-Q1) of severity ranks per fid.

fid_severity_rank_iqr(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_iqr (item 730).
< 3 problems per fid -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND IQR not range;
     fid 'f1': INFO(0)+LOW(1)+HIGH(3)+CRITICAL(4) -> IQR=3.0;
     class-outer gives key='A' wrong; range-impl gives 4.0 wrong.
  2. < 3 problems per fid -> 0.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_iqr


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_iqr_not_range_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND IQR not range.

    fid 'f1': INFO+LOW+HIGH+CRITICAL -> sorted [0,1,3,4] -> IQR=3.0.
    class-outer gives key='A' wrong; range-impl gives 4.0 wrong.
    """
    problems = [_p("f1", "INFO"), _p("f1", "LOW"), _p("f1", "HIGH"), _p("f1", "CRITICAL")]
    result = fid_severity_rank_iqr(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 3.0, abs_tol=1e-9), (
        f"INFO+LOW+HIGH+CRIT: IQR=3.0; got {got} (range=4.0 wrong)"
    )


def test_fewer_than_3_gives_zero() -> None:
    """< 3 problems per fid -> 0.0."""
    result = fid_severity_rank_iqr([_p("f2", "CRITICAL"), _p("f2", "INFO")])
    got = result.get("f2")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"2 problems -> 0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_iqr([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid computes independently."""
    problems = [_p("f3", "INFO"), _p("f3", "LOW"), _p("f3", "HIGH"), _p("f3", "CRITICAL")]
    problems += [_p("f4", "MEDIUM")] * 4
    result = fid_severity_rank_iqr(problems)
    assert math.isclose(result["f3"], 3.0, abs_tol=1e-9), f"f3: IQR=3.0; got {result.get('f3')}"
    assert math.isclose(result["f4"], 0.0, abs_tol=1e-9), (
        f"f4: all MEDIUM -> 0.0; got {result.get('f4')}"
    )


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f5", "INFO"), _p("f5", "MEDIUM"), _p("f5", "CRITICAL")]
    result = fid_severity_rank_iqr(problems)
    assert isinstance(result["f5"], float), f"Must be float; got {type(result['f5'])}"
