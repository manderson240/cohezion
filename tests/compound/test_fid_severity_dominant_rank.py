"""Item 853: fid_severity_dominant_rank() -- dominant rank by rank*count per fid."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_dominant_rank


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_weighted_not_frequency_primary_discriminator() -> None:
    # fid f1: 4 INFO(0)+1 HIGH(3) -> weighted HIGH(3)=3 > INFO(0)=0; class-outer wrong; mode=0 wrong
    problems = [_p("A", "f1", "INFO")] * 4 + [_p("A", "f1", "HIGH")]
    result = fid_severity_dominant_rank(problems)
    assert "f1" in result and "A" not in result
    assert result["f1"] == 3


def test_all_same_rank_returns_that_rank() -> None:
    problems = [_p("A", "f2", "HIGH")] * 3
    result = fid_severity_dominant_rank(problems)
    assert result["f2"] == 3


def test_tie_broken_by_highest_rank() -> None:
    # LOW(1)*2=2, MEDIUM(2)*1=2 -> tie -> highest=2
    problems = [_p("A", "f3", "LOW")] * 2 + [_p("A", "f3", "MEDIUM")]
    result = fid_severity_dominant_rank(problems)
    assert result["f3"] == 2


def test_multiple_fids_independent() -> None:
    # f10: 2 INFO+1 HIGH -> HIGH(3); f11: 3 CRITICAL -> CRITICAL(4)
    problems = (
        [_p("X", "f10", "INFO")] * 2 + [_p("X", "f10", "HIGH")] + [_p("Y", "f11", "CRITICAL")] * 3
    )
    result = fid_severity_dominant_rank(problems)
    assert result["f10"] == 3
    assert result["f11"] == 4


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_dominant_rank([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("A", "f4", "MEDIUM")]
    result = fid_severity_dominant_rank(problems)
    assert isinstance(result["f4"], int)


def test_single_problem_returns_its_rank() -> None:
    problems = [_p("A", "f5", "LOW")]
    result = fid_severity_dominant_rank(problems)
    assert result["f5"] == 1


def test_higher_count_low_rank_vs_lower_count_high_rank() -> None:
    # 5 LOW(1)*5=5 vs 1 CRITICAL(4)*1=4 -> LOW wins
    problems = [_p("A", "f6", "LOW")] * 5 + [_p("A", "f6", "CRITICAL")]
    result = fid_severity_dominant_rank(problems)
    assert result["f6"] == 1


def test_critical_dominates_multiple() -> None:
    # 2 CRITICAL(4)*2=8 vs 3 HIGH(3)*3=9 -> HIGH wins
    problems = [_p("A", "f7", "CRITICAL")] * 2 + [_p("A", "f7", "HIGH")] * 3
    result = fid_severity_dominant_rank(problems)
    assert result["f7"] == 3


def test_all_info_gives_zero() -> None:
    problems = [_p("A", "f8", "INFO")] * 4
    result = fid_severity_dominant_rank(problems)
    assert result["f8"] == 0
