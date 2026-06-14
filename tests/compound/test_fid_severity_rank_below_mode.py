"""Item 783: fid_severity_rank_below_mode() -- fraction below modal rank per fid.

fid_severity_rank_below_mode(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_below_mode (item 782).
Modal rank = most frequent; tie -> min rank.
fraction = count(rank < modal_rank) / n.
All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [CRITICAL(4)*3, INFO(0)*2]
     -> modal_rank=4, count(<4)=2/5=0.4; class-outer wrong; above_mode=0.0 wrong.
  2. Modal at bottom -> 0.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_below_mode


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_below_mode_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; below_mode=0.4; above_mode=0.0 wrong.

    fid f1: [CRITICAL(4)*3, INFO(0)*2] -> modal_rank=4, count(<4)=2/5=0.4.
    """
    problems = [_p("f1", "CRITICAL")] * 3 + [_p("f1", "INFO")] * 2
    result = fid_severity_rank_below_mode(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 0.4, abs_tol=1e-9), f"CRITICAL*3+INFO*2 -> below_mode=0.4; got {got}"
    assert not math.isclose(got, 0.0, abs_tol=1e-6), "Must be below not above (0.0 is above_mode)"


def test_modal_at_bottom_gives_zero() -> None:
    """Modal rank at minimum -> below = 0.0."""
    problems = [_p("f2", "INFO")] * 3 + [_p("f2", "HIGH")] * 2
    result = fid_severity_rank_below_mode(problems)
    got = result.get("f2")
    # modal_rank=0 (INFO); count(<0)=0
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"INFO*3+HIGH*2 -> below_mode=0.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_below_mode([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = (
        [_p("fA", "CRITICAL")] * 3
        + [_p("fA", "INFO")] * 2  # below=0.4
        + [_p("fB", "INFO")] * 3  # all-same -> 0.0
    )
    result = fid_severity_rank_below_mode(problems)
    assert math.isclose(result["fA"], 0.4, abs_tol=1e-9), f"fA -> 0.4; got {result['fA']}"
    assert math.isclose(result["fB"], 0.0, abs_tol=1e-9), f"fB -> 0.0; got {result['fB']}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f3", "CRITICAL"), _p("f3", "CRITICAL"), _p("f3", "INFO")]
    result = fid_severity_rank_below_mode(problems)
    assert isinstance(result["f3"], float), f"Must be float; got {type(result['f3'])}"
