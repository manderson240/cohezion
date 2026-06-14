"""Item 823: fid_max_severity_rank() -- maximum severity rank per fid."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_max_severity_rank


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_max_rank_primary_discriminator() -> None:
    # fid f1 has INFO(0), LOW(1), HIGH(3) -> max rank = 3; class-outer wrong; mean wrong
    problems = [_p("A", "f1", "INFO"), _p("A", "f1", "LOW"), _p("B", "f1", "HIGH")]
    result = fid_max_severity_rank(problems)
    assert "f1" in result and "A" not in result
    assert result["f1"] == 3


def test_single_problem_returns_its_rank() -> None:
    problems = [_p("B", "f2", "CRITICAL")]
    result = fid_max_severity_rank(problems)
    assert result["f2"] == 4


def test_multiple_fids_independent() -> None:
    problems = [
        _p("X", "f10", "MEDIUM"),
        _p("X", "f10", "LOW"),
        _p("Y", "f11", "INFO"),
        _p("Y", "f11", "CRITICAL"),
    ]
    result = fid_max_severity_rank(problems)
    assert result.get("f10") == 2 and result.get("f11") == 4


def test_empty_returns_empty_dict() -> None:
    assert fid_max_severity_rank([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("D", "f99", "HIGH"), _p("D", "f99", "LOW")]
    result = fid_max_severity_rank(problems)
    assert isinstance(result["f99"], int)
