"""Item 845: fid_weighted_severity_score() -- sum of severity ranks per fid."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_weighted_severity_score


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_sum_not_count_primary_discriminator() -> None:
    # fid f1: INFO(0)+LOW(1)+HIGH(3) -> sum=4; class-outer wrong; count=3 wrong
    problems = [_p("A", "f1", "INFO"), _p("A", "f1", "LOW"), _p("B", "f1", "HIGH")]
    result = fid_weighted_severity_score(problems)
    assert "f1" in result and "A" not in result
    assert result["f1"] == 4


def test_all_info_gives_zero_score() -> None:
    problems = [_p("B", "f2", "INFO")] * 5
    result = fid_weighted_severity_score(problems)
    assert result["f2"] == 0


def test_multiple_fids_independent() -> None:
    problems = [_p("X", "f10", "CRITICAL")] * 2 + [_p("Y", "f11", "LOW")] * 3
    result = fid_weighted_severity_score(problems)
    assert result.get("f10") == 8 and result.get("f11") == 3


def test_empty_returns_empty_dict() -> None:
    assert fid_weighted_severity_score([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("D", "f99", "HIGH"), _p("D", "f99", "LOW")]
    result = fid_weighted_severity_score(problems)
    assert isinstance(result["f99"], int)
