"""Item 795: fid_severity_rank_medium_fraction() -- fraction MEDIUM per fid.

fid_severity_rank_medium_fraction(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_medium_fraction (item 794).
fraction = count(rank == 2) / n per fid.  All LOW/HIGH -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [LOW*3, MEDIUM*2] -> 0.4;
     class-outer wrong; low_frac=0.6 wrong.
  2. All HIGH per fid -> 0.0 (rank 3, not 2).
  3. Multi-fid independent counts.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_medium_fraction


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="X", finding_id=fid, severity=sev)


def test_fid_outer_key_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; fid f1: [LOW*3, MEDIUM*2] -> 0.4."""
    problems = [_p("f1", "LOW")] * 3 + [_p("f1", "MEDIUM")] * 2
    result = fid_severity_rank_medium_fraction(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 0.4, abs_tol=1e-9), f"[LOW*3,MED*2] -> 0.4; got {got}"
    assert not math.isclose(got, 0.6, abs_tol=1e-6), "LOW must not be counted (0.6 wrong)"


def test_all_high_gives_zero() -> None:
    """All HIGH (rank=3) -> medium_fraction=0.0."""
    problems = [_p("f2", "HIGH")] * 3
    result = fid_severity_rank_medium_fraction(problems)
    assert math.isclose(result["f2"], 0.0, abs_tol=1e-9), f"All HIGH -> 0.0; got {result['f2']}"


def test_multi_fid_independent() -> None:
    """Each fid's fraction independently computed."""
    problems = (
        [_p("f3", "MEDIUM")] * 2 + [_p("f3", "HIGH")]
        + [_p("f4", "MEDIUM")] * 3 + [_p("f4", "CRITICAL")]
    )
    result = fid_severity_rank_medium_fraction(problems)
    # f3: 2/3~0.667; f4: 3/4=0.75
    assert math.isclose(result["f3"], 2/3, abs_tol=1e-9), f"f3: [MED*2,HIGH] -> 2/3; got {result['f3']}"
    assert math.isclose(result["f4"], 0.75, abs_tol=1e-9), f"f4: [MED*3,CRIT] -> 0.75; got {result['f4']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_medium_fraction([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f5", "MEDIUM"), _p("f5", "INFO")]
    result = fid_severity_rank_medium_fraction(problems)
    assert isinstance(result["f5"], float), f"Must be float; got {type(result['f5'])}"
