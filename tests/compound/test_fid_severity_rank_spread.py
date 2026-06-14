"""Item 829: fid_severity_rank_spread() -- max minus min severity rank per fid."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_spread


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_spread_primary_discriminator() -> None:
    # fid f1: INFO(0)+LOW(1)+HIGH(3) -> spread=3; class-outer wrong; max=3 wrong
    problems = [_p("A", "f1", "INFO"), _p("A", "f1", "LOW"), _p("B", "f1", "HIGH")]
    result = fid_severity_rank_spread(problems)
    assert "f1" in result and "A" not in result
    assert result["f1"] == 3


def test_single_problem_gives_zero_spread() -> None:
    problems = [_p("B", "f2", "CRITICAL")]
    result = fid_severity_rank_spread(problems)
    assert result["f2"] == 0


def test_multiple_fids_independent() -> None:
    problems = [
        _p("X", "f10", "INFO"),
        _p("X", "f10", "CRITICAL"),
        _p("Y", "f11", "LOW"),
        _p("Y", "f11", "MEDIUM"),
    ]
    result = fid_severity_rank_spread(problems)
    assert result.get("f10") == 4 and result.get("f11") == 1


def test_uniform_severity_gives_zero_spread() -> None:
    problems = [_p("C", "f3", "HIGH"), _p("C", "f3", "HIGH")]
    result = fid_severity_rank_spread(problems)
    assert result["f3"] == 0


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_spread([]) == {}
