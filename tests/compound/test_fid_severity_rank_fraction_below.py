"""Item 795: fid_severity_rank_fraction_below() -- fraction below threshold per fid.

fid_severity_rank_fraction_below(problems, threshold: int) -> dict[str, float].
Fid-axis complement of class_severity_rank_fraction_below (item 788).
fraction = count(rank < threshold) / n per fid.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [CRIT(4)*3,HIGH(3)*2] fraction_below(4)=0.4;
     class-outer wrong; fraction_at_or_above(4)=0.6 wrong.
  2. All above threshold -> 0.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_fraction_below


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_fraction_below_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; fraction_below(4)=0.4; class-outer wrong.

    fid f1: [CRITICAL(4)*3, HIGH(3)*2] -> count(rank<4)=2/5=0.4.
    """
    problems = [_p("f1", "CRITICAL")] * 3 + [_p("f1", "HIGH")] * 2
    result = fid_severity_rank_fraction_below(problems, 4)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 0.4, abs_tol=1e-9), f"fraction_below(4)=0.4; got {got}"
    assert not math.isclose(got, 0.6, abs_tol=1e-6), "Must be below not at-or-above (0.6)"


def test_all_at_or_above_threshold_gives_zero() -> None:
    """All ranks at or above threshold -> fraction_below = 0.0."""
    problems = [_p("f2", "CRITICAL")] * 3  # rank=4, threshold=4
    result = fid_severity_rank_fraction_below(problems, 4)
    got = result.get("f2")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"All CRITICAL(4) below threshold=4 -> 0.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_fraction_below([], 3) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = (
        [_p("fA", "CRITICAL")] * 3
        + [_p("fA", "HIGH")] * 2  # below(4)=0.4
        + [_p("fB", "HIGH")] * 4  # below(4)=1.0 (all HIGH(3) < 4)
    )
    result = fid_severity_rank_fraction_below(problems, 4)
    assert math.isclose(result["fA"], 0.4, abs_tol=1e-9), f"fA -> 0.4; got {result['fA']}"
    assert math.isclose(result["fB"], 1.0, abs_tol=1e-9), f"fB -> 1.0; got {result['fB']}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f3", "CRITICAL"), _p("f3", "INFO")]
    result = fid_severity_rank_fraction_below(problems, 4)
    assert isinstance(result["f3"], float), f"Must be float; got {type(result['f3'])}"
