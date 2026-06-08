"""Item 781: fid_severity_rank_above_mode() -- fraction above modal rank per fid.

fid_severity_rank_above_mode(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_above_mode (item 780).
Modal rank = most frequent rank; tie -> min rank.
fraction = count(rank > modal_rank) / n.
All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; [INFO(0)*2, HIGH(3)*2, CRITICAL(4)]
     -> modal_rank=0, above_mode=3/5=0.6; above-median=0.2 wrong; class-outer wrong.
  2. All-same -> 0.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_above_mode


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_above_mode_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; above_mode=0.6; above_median=0.2 wrong.

    fid f1: [INFO(0)*2, HIGH(3)*2, CRITICAL(4)] -> modal_rank=0, count(>0)=3/5=0.6.
    """
    problems = [_p("f1", "INFO")] * 2 + [_p("f1", "HIGH")] * 2 + [_p("f1", "CRITICAL")]
    result = fid_severity_rank_above_mode(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 0.6, abs_tol=1e-9), (
        f"[INFO*2,HIGH*2,CRITICAL] -> above_mode=0.6; got {got}"
    )
    assert not math.isclose(got, 0.2, abs_tol=1e-6), "Must be above_mode not above_median (0.2)"


def test_all_same_gives_zero() -> None:
    """All same -> above_mode = 0.0."""
    problems = [_p("f2", "CRITICAL")] * 3
    result = fid_severity_rank_above_mode(problems)
    got = result.get("f2")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"All CRITICAL -> above_mode=0.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_above_mode([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = (
        [_p("fA", "INFO")] * 2 + [_p("fA", "HIGH")] * 2 + [_p("fA", "CRITICAL")]  # 0.6
        + [_p("fB", "INFO")] * 3  # all-same -> 0.0
    )
    result = fid_severity_rank_above_mode(problems)
    assert math.isclose(result["fA"], 0.6, abs_tol=1e-9), f"fA -> 0.6; got {result['fA']}"
    assert math.isclose(result["fB"], 0.0, abs_tol=1e-9), f"fB -> 0.0; got {result['fB']}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f3", "INFO"), _p("f3", "INFO"), _p("f3", "CRITICAL")]
    result = fid_severity_rank_above_mode(problems)
    assert isinstance(result["f3"], float), f"Must be float; got {type(result['f3'])}"
