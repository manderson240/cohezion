"""Item 777: fid_severity_rank_mode_value() -- modal severity rank per fid.

fid_severity_rank_mode_value(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_mode_value (item 776).
Most frequent rank per fid; tie -> min rank; empty -> {}; pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [CRITICAL(4)*3, INFO(0)*2] -> mode=4.0;
     class-outer gives 'A' wrong; mean=2.4 wrong.
  2. Tie-break -> min rank.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_mode_value


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_mode_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; mode=4.0; class-outer wrong; mean=2.4 wrong.

    fid f1: [CRITICAL(4)*3, INFO(0)*2] -> counts={4:3, 0:2}, mode=4.
    """
    problems = [_p("f1", "CRITICAL")] * 3 + [_p("f1", "INFO")] * 2
    result = fid_severity_rank_mode_value(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 4.0, abs_tol=1e-9), f"CRITICAL*3+INFO*2 -> mode=4.0; got {got}"
    assert not math.isclose(got, 2.4, abs_tol=1e-6), "Must be mode not mean (2.4)"


def test_tie_break_gives_min_rank() -> None:
    """Tie -> min rank: [INFO(0)*2, HIGH(3)*2] -> mode=0.0 (min of 0,3)."""
    problems = [_p("f2", "INFO")] * 2 + [_p("f2", "HIGH")] * 2
    result = fid_severity_rank_mode_value(problems)
    got = result.get("f2")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"tie INFO+HIGH -> min=0.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_mode_value([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = (
        [_p("fA", "CRITICAL")] * 3
        + [_p("fA", "INFO")] * 2  # mode=4.0
        + [_p("fB", "INFO")] * 3  # all-same -> 0.0
    )
    result = fid_severity_rank_mode_value(problems)
    assert math.isclose(result["fA"], 4.0, abs_tol=1e-9), f"fA -> mode=4.0; got {result['fA']}"
    assert math.isclose(result["fB"], 0.0, abs_tol=1e-9), f"fB -> mode=0.0; got {result['fB']}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f3", "INFO"), _p("f3", "INFO"), _p("f3", "CRITICAL")]
    result = fid_severity_rank_mode_value(problems)
    assert isinstance(result["f3"], float), f"Must be float; got {type(result['f3'])}"
