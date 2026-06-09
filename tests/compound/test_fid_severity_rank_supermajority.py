"""Item 859: fid_severity_rank_supermajority() -- 2/3 threshold rank indicator per fid."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_supermajority


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_supermajority_not_majority_primary_discriminator() -> None:
    # fid f1: 3 HIGH + 2 LOW -> 3/5=0.6 < 2/3 -> False; class-outer wrong; majority wrong
    problems = [_p("A", "f1", "HIGH")] * 3 + [_p("B", "f1", "LOW")] * 2
    result = fid_severity_rank_supermajority(problems)
    assert "f1" in result and "A" not in result
    assert result["f1"] is False


def test_exactly_two_thirds_gives_true() -> None:
    problems = [_p("A", "f2", "CRITICAL")] * 2 + [_p("A", "f2", "HIGH")]
    result = fid_severity_rank_supermajority(problems)
    assert result["f2"] is True


def test_single_problem_gives_true() -> None:
    problems = [_p("A", "f3", "LOW")]
    result = fid_severity_rank_supermajority(problems)
    assert result["f3"] is True


def test_all_same_rank_gives_true() -> None:
    problems = [_p("A", "f4", "MEDIUM")] * 4
    result = fid_severity_rank_supermajority(problems)
    assert result["f4"] is True


def test_50_50_split_gives_false() -> None:
    problems = [_p("A", "f5", "HIGH")] * 2 + [_p("A", "f5", "LOW")] * 2
    result = fid_severity_rank_supermajority(problems)
    assert result["f5"] is False


def test_multiple_fids_independent() -> None:
    # f10: 2 HIGH+1 LOW -> True; f11: 3 HIGH+2 LOW -> False
    problems = ([_p("X", "f10", "HIGH")] * 2 + [_p("X", "f10", "LOW")] +
                [_p("Y", "f11", "HIGH")] * 3 + [_p("Y", "f11", "LOW")] * 2)
    result = fid_severity_rank_supermajority(problems)
    assert result["f10"] is True
    assert result["f11"] is False


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_supermajority([]) == {}


def test_return_type_is_bool() -> None:
    problems = [_p("A", "f6", "CRITICAL"), _p("A", "f6", "CRITICAL"), _p("A", "f6", "LOW")]
    result = fid_severity_rank_supermajority(problems)
    assert isinstance(result["f6"], bool)


def test_three_equal_thirds_gives_false() -> None:
    problems = [_p("A", "f7", "INFO"), _p("A", "f7", "LOW"), _p("A", "f7", "HIGH")]
    result = fid_severity_rank_supermajority(problems)
    assert result["f7"] is False


def test_75_percent_gives_true() -> None:
    problems = [_p("A", "f8", "CRITICAL")] * 3 + [_p("A", "f8", "HIGH")]
    result = fid_severity_rank_supermajority(problems)
    assert result["f8"] is True
