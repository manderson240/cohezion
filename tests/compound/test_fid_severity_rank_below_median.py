"""Item 760: fid_severity_rank_below_median() -- fraction below median rank per fid.

fid_severity_rank_below_median(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_below_median (item 759).
fraction = count(rank < median) / n per fid.
All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: CRITICAL*2+INFO -> fraction=1/3;
     class-outer gives 'A' wrong; above-impl gives 0.0 wrong.
  2. All-same -> 0.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_below_median


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_below_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; fraction=1/3; above-impl gives 0.0 wrong.

    fid f1: CRITICAL(4)*2+INFO(0) -> sorted=[0,4,4], median=4, count(<4)=1, fraction=1/3.
    """
    problems = [_p("f1", "CRITICAL"), _p("f1", "CRITICAL"), _p("f1", "INFO")]
    result = fid_severity_rank_below_median(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 1 / 3, abs_tol=1e-9), (
        f"CRITICAL*2+INFO -> below=1/3~{1 / 3:.6f}; got {got}"
    )


def test_all_same_gives_zero() -> None:
    """All same severity -> fraction = 0.0."""
    problems = [_p("f2", "LOW")] * 3
    result = fid_severity_rank_below_median(problems)
    got = result.get("f2")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), f"All LOW -> 0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_below_median([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = [
        _p("fA", "CRITICAL"),
        _p("fA", "CRITICAL"),
        _p("fA", "INFO"),  # 1/3
        _p("fB", "HIGH"),
        _p("fB", "HIGH"),  # all-same -> 0.0
    ]
    result = fid_severity_rank_below_median(problems)
    assert math.isclose(result["fA"], 1 / 3, abs_tol=1e-9), f"fA -> 1/3; got {result['fA']}"
    assert math.isclose(result["fB"], 0.0, abs_tol=1e-9), f"fB -> 0.0; got {result['fB']}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f3", "CRITICAL"), _p("f3", "INFO")]
    result = fid_severity_rank_below_median(problems)
    assert isinstance(result["f3"], float), f"Must be float; got {type(result['f3'])}"
