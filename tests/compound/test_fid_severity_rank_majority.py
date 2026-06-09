"""Item 857: fid_severity_rank_majority() -- strict majority rank indicator per fid."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_majority


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_strict_majority_primary_discriminator() -> None:
    # fid f1: 3 HIGH + 3 LOW -> 50/50 -> False; class-outer wrong; >= 0.5 wrong
    problems = [_p("A", "f1", "HIGH")] * 3 + [_p("B", "f1", "LOW")] * 3
    result = fid_severity_rank_majority(problems)
    assert "f1" in result and "A" not in result
    assert result["f1"] is False


def test_majority_when_one_rank_dominates() -> None:
    problems = [_p("A", "f2", "CRITICAL")] * 3 + [_p("A", "f2", "HIGH")] * 2
    result = fid_severity_rank_majority(problems)
    assert result["f2"] is True


def test_single_problem_gives_true() -> None:
    problems = [_p("A", "f3", "HIGH")]
    result = fid_severity_rank_majority(problems)
    assert result["f3"] is True


def test_all_same_rank_gives_true() -> None:
    problems = [_p("A", "f4", "LOW")] * 4
    result = fid_severity_rank_majority(problems)
    assert result["f4"] is True


def test_three_equal_ranks_gives_false() -> None:
    problems = [_p("A", "f5", "LOW")] * 2 + [_p("A", "f5", "MEDIUM")] * 2 + [_p("A", "f5", "HIGH")] * 2
    result = fid_severity_rank_majority(problems)
    assert result["f5"] is False


def test_multiple_fids_independent() -> None:
    problems = ([_p("X", "f10", "HIGH")] * 4 + [_p("X", "f10", "LOW")] +
                [_p("Y", "f11", "HIGH")] * 3 + [_p("Y", "f11", "LOW")] * 3)
    result = fid_severity_rank_majority(problems)
    assert result["f10"] is True
    assert result["f11"] is False


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_majority([]) == {}


def test_return_type_is_bool() -> None:
    problems = [_p("A", "f6", "CRITICAL"), _p("A", "f6", "LOW")]
    result = fid_severity_rank_majority(problems)
    assert isinstance(result["f6"], bool)


def test_exactly_51_percent_gives_true() -> None:
    problems = [_p("A", "f7", "CRITICAL")] * 51 + [_p("A", "f7", "HIGH")] * 49
    result = fid_severity_rank_majority(problems)
    assert result["f7"] is True


def test_four_equal_ranks_gives_false() -> None:
    problems = [_p("A", "f8", s) for s in ["INFO", "LOW", "MEDIUM", "HIGH"]]
    result = fid_severity_rank_majority(problems)
    assert result["f8"] is False
