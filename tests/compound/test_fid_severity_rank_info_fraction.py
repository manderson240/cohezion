"""Item 793: fid_severity_rank_info_fraction() -- fraction INFO per fid.

fid_severity_rank_info_fraction(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_info_fraction (item 792).
fraction = count(rank == 0) / n per fid.  All LOW -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [INFO*2, LOW*3] -> 0.4;
     class-outer wrong; low_frac=1.0 wrong.
  2. All LOW per fid -> 0.0.
  3. Multi-fid independent counts.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_info_fraction


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="X", finding_id=fid, severity=sev)


def test_fid_outer_key_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; fid f1: [INFO*2, LOW*3] -> 0.4."""
    problems = [_p("f1", "INFO")] * 2 + [_p("f1", "LOW")] * 3
    result = fid_severity_rank_info_fraction(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 0.4, abs_tol=1e-9), f"[INFO*2,LOW*3] -> 0.4; got {got}"
    assert not math.isclose(got, 1.0, abs_tol=1e-6), "Must be info-only not low_fraction"


def test_all_low_gives_zero() -> None:
    """All LOW per fid -> 0.0."""
    problems = [_p("f2", "LOW")] * 3
    result = fid_severity_rank_info_fraction(problems)
    assert math.isclose(result["f2"], 0.0, abs_tol=1e-9), f"All LOW -> 0.0; got {result['f2']}"


def test_multi_fid_independent() -> None:
    """Each fid's fraction independently computed."""
    problems = (
        [_p("f3", "INFO")] * 3 + [_p("f3", "LOW")]
        + [_p("f4", "INFO")] + [_p("f4", "CRITICAL")] * 3
    )
    result = fid_severity_rank_info_fraction(problems)
    # f3: 3/4=0.75; f4: 1/4=0.25
    assert math.isclose(result["f3"], 0.75, abs_tol=1e-9), f"f3: [INFO*3,LOW] -> 0.75; got {result['f3']}"
    assert math.isclose(result["f4"], 0.25, abs_tol=1e-9), f"f4: [INFO,CRIT*3] -> 0.25; got {result['f4']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_info_fraction([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f5", "INFO"), _p("f5", "CRITICAL")]
    result = fid_severity_rank_info_fraction(problems)
    assert isinstance(result["f5"], float), f"Must be float; got {type(result['f5'])}"
