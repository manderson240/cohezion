"""Item 841: fid_severity_rank_mode() -- most frequent severity rank per fid."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_mode


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_mode_rank_primary_discriminator() -> None:
    # fid f1: INFO(0)*3 + HIGH(3)*2 -> mode rank=0; class-outer wrong; max=3 wrong
    problems = [_p("A", "f1", "INFO")] * 3 + [_p("A", "f1", "HIGH")] * 2
    result = fid_severity_rank_mode(problems)
    assert "f1" in result and "A" not in result
    assert result["f1"] == 0


def test_tie_broken_by_lowest_rank() -> None:
    problems = [_p("B", "f2", "LOW")] * 2 + [_p("B", "f2", "HIGH")] * 2
    result = fid_severity_rank_mode(problems)
    assert result["f2"] == 1


def test_single_problem_returns_its_rank() -> None:
    problems = [_p("B", "f3", "CRITICAL")]
    result = fid_severity_rank_mode(problems)
    assert result["f3"] == 4


def test_multiple_fids_independent() -> None:
    problems = [_p("X", "f10", "HIGH")] * 5 + [_p("X", "f10", "LOW")] * 1 + [_p("Y", "f11", "INFO")] * 3
    result = fid_severity_rank_mode(problems)
    assert result.get("f10") == 3 and result.get("f11") == 0


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_mode([]) == {}
