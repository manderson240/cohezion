"""Item 809: fid_severity_rank_low_only_fraction() -- fraction rank==1 (LOW only) per fid.

fid_severity_rank_low_only_fraction(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_low_only_fraction (item 808).
fraction = count(rank == 1) / n per fid.  INFO not included.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [LOW*3,INFO*2] -> 3/5=0.6; class-outer wrong; low_fraction=1.0 wrong.
  2. INFO-only fid -> 0.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_low_only_fraction


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_low_only_fraction_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key=FID; fid f1: [LOW*3,INFO*2] -> 3/5=0.6; class-outer wrong."""
    problems = (
        [_p("A", "f1", "LOW")] * 3 + [_p("A", "f1", "INFO")] * 2 +
        [_p("B", "f2", "LOW")] * 1
    )
    result = fid_severity_rank_low_only_fraction(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be key; got {list(result)}"
    assert "A" not in result, "Must be keyed by FID not class"
    assert math.isclose(result["f1"], 0.6, abs_tol=1e-9), (
        f"fid f1: LOW*3,INFO*2 -> 0.6; got {result['f1']}"
    )
    assert math.isclose(result["f2"], 1.0, abs_tol=1e-9), f"fid f2: LOW*1 -> 1.0; got {result['f2']}"


def test_info_only_gives_zero() -> None:
    """INFO-only fid -> 0.0 (INFO not counted as LOW)."""
    problems = [_p("B", "f3", "INFO")] * 4
    result = fid_severity_rank_low_only_fraction(problems)
    assert "f3" in result, "Fid f3 must appear"
    assert math.isclose(result["f3"], 0.0, abs_tol=1e-9), f"All INFO -> 0.0; got {result['f3']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_low_only_fraction([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids are computed independently."""
    problems = (
        [_p("X", "f10", "LOW")] * 2 + [_p("X", "f10", "INFO")] * 2 +
        [_p("X", "f11", "INFO")] * 3
    )
    result = fid_severity_rank_low_only_fraction(problems)
    assert math.isclose(result.get("f10", -1), 0.5, abs_tol=1e-9), f"f10 -> 0.5; got {result.get('f10')}"
    assert math.isclose(result.get("f11", -1), 0.0, abs_tol=1e-9), f"f11 -> 0.0; got {result.get('f11')}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "f99", "LOW"), _p("D", "f99", "HIGH")]
    result = fid_severity_rank_low_only_fraction(problems)
    assert isinstance(result["f99"], float), f"Must be float; got {type(result['f99'])}"
