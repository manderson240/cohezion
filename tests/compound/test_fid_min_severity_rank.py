"""Item 825: fid_min_severity_rank() -- minimum severity rank per fid."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_min_severity_rank


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_min_rank_primary_discriminator() -> None:
    # fid f1 has INFO(0), LOW(1), HIGH(3) -> min rank = 0; max=3 wrong; class-outer wrong
    problems = [_p("A", "f1", "INFO"), _p("A", "f1", "LOW"), _p("B", "f1", "HIGH")]
    result = fid_min_severity_rank(problems)
    assert "f1" in result and "A" not in result
    assert result["f1"] == 0


def test_single_critical_returns_four() -> None:
    problems = [_p("B", "f2", "CRITICAL")]
    result = fid_min_severity_rank(problems)
    assert result["f2"] == 4


def test_multiple_fids_independent() -> None:
    problems = [
        _p("X", "f10", "MEDIUM"),
        _p("X", "f10", "LOW"),
        _p("Y", "f11", "INFO"),
        _p("Y", "f11", "CRITICAL"),
    ]
    result = fid_min_severity_rank(problems)
    assert result.get("f10") == 1 and result.get("f11") == 0


def test_empty_returns_empty_dict() -> None:
    assert fid_min_severity_rank([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("D", "f99", "HIGH"), _p("D", "f99", "LOW")]
    result = fid_min_severity_rank(problems)
    assert isinstance(result["f99"], int)
