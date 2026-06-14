"""Item 856: class_severity_rank_majority() -- strict majority (>50%) rank indicator per class."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_majority


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_strict_majority_not_50_50_primary_discriminator() -> None:
    # class A: 3 HIGH + 3 LOW -> 50/50 -> False; >= 0.5 impl would give True (wrong)
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")] * 3
    result = class_severity_rank_majority(problems)
    assert result["A"] is False


def test_strict_majority_when_one_rank_dominates() -> None:
    # class B: 3 HIGH + 2 LOW -> HIGH is 3/5=0.6 > 0.5 -> True
    problems = [_p("B", "HIGH")] * 3 + [_p("B", "LOW")] * 2
    result = class_severity_rank_majority(problems)
    assert result["B"] is True


def test_single_problem_gives_true() -> None:
    # Only one problem: its rank has 100% share
    problems = [_p("C", "CRITICAL")]
    result = class_severity_rank_majority(problems)
    assert result["C"] is True


def test_all_same_rank_gives_true() -> None:
    problems = [_p("D", "HIGH")] * 5
    result = class_severity_rank_majority(problems)
    assert result["D"] is True


def test_three_equal_ranks_gives_false() -> None:
    # 2 INFO + 2 LOW + 2 HIGH: each is 2/6=0.333 -> False
    problems = [_p("E", "INFO")] * 2 + [_p("E", "LOW")] * 2 + [_p("E", "HIGH")] * 2
    result = class_severity_rank_majority(problems)
    assert result["E"] is False


def test_multiple_classes_independent() -> None:
    # X: 4 HIGH + 1 LOW -> 4/5=0.8 -> True; Y: 3 HIGH + 3 LOW -> False
    problems = (
        [_p("X", "HIGH")] * 4 + [_p("X", "LOW")] + [_p("Y", "HIGH")] * 3 + [_p("Y", "LOW")] * 3
    )
    result = class_severity_rank_majority(problems)
    assert result["X"] is True
    assert result["Y"] is False


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_majority([]) == {}


def test_return_type_is_bool() -> None:
    problems = [_p("F", "HIGH"), _p("F", "LOW")]
    result = class_severity_rank_majority(problems)
    assert isinstance(result["F"], bool)


def test_exactly_51_percent_gives_true() -> None:
    # 51 HIGH + 49 LOW -> 51/100 = 0.51 > 0.5 -> True
    problems = [_p("G", "HIGH")] * 51 + [_p("G", "LOW")] * 49
    result = class_severity_rank_majority(problems)
    assert result["G"] is True


def test_four_ranks_each_25_percent_gives_false() -> None:
    problems = [_p("H", s) for s in ["INFO", "LOW", "MEDIUM", "HIGH"]]
    result = class_severity_rank_majority(problems)
    assert result["H"] is False
