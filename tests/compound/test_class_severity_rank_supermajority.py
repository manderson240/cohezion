"""Item 858: class_severity_rank_supermajority() -- 2/3 threshold rank indicator per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_supermajority


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_supermajority_not_majority_primary_discriminator() -> None:
    # class A: 3 HIGH + 2 LOW -> HIGH is 3/5=0.6 < 2/3 -> False
    # majority (>0.5) impl would return True (wrong)
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")] * 2
    result = class_severity_rank_supermajority(problems)
    assert result["A"] is False


def test_exactly_two_thirds_gives_true() -> None:
    # 2 HIGH + 1 LOW -> HIGH is 2/3 >= 2/3 -> True
    problems = [_p("B", "HIGH")] * 2 + [_p("B", "LOW")]
    result = class_severity_rank_supermajority(problems)
    assert result["B"] is True


def test_single_problem_gives_true() -> None:
    problems = [_p("C", "CRITICAL")]
    result = class_severity_rank_supermajority(problems)
    assert result["C"] is True


def test_all_same_rank_gives_true() -> None:
    problems = [_p("D", "LOW")] * 5
    result = class_severity_rank_supermajority(problems)
    assert result["D"] is True


def test_50_50_split_gives_false() -> None:
    problems = [_p("E", "HIGH")] * 3 + [_p("E", "LOW")] * 3
    result = class_severity_rank_supermajority(problems)
    assert result["E"] is False


def test_three_equal_thirds_gives_false() -> None:
    # 1 INFO + 1 LOW + 1 HIGH: each is 1/3 < 2/3 -> False
    problems = [_p("F", "INFO"), _p("F", "LOW"), _p("F", "HIGH")]
    result = class_severity_rank_supermajority(problems)
    assert result["F"] is False


def test_multiple_classes_independent() -> None:
    # X: 2 HIGH + 1 LOW -> 2/3 -> True; Y: 3 HIGH + 2 LOW -> 3/5 -> False
    problems = ([_p("X", "HIGH")] * 2 + [_p("X", "LOW")] +
                [_p("Y", "HIGH")] * 3 + [_p("Y", "LOW")] * 2)
    result = class_severity_rank_supermajority(problems)
    assert result["X"] is True
    assert result["Y"] is False


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_supermajority([]) == {}


def test_return_type_is_bool() -> None:
    problems = [_p("G", "HIGH"), _p("G", "HIGH"), _p("G", "LOW")]
    result = class_severity_rank_supermajority(problems)
    assert isinstance(result["G"], bool)


def test_75_percent_gives_true() -> None:
    # 3 HIGH + 1 LOW -> 3/4=0.75 >= 2/3 -> True
    problems = [_p("H", "HIGH")] * 3 + [_p("H", "LOW")]
    result = class_severity_rank_supermajority(problems)
    assert result["H"] is True
