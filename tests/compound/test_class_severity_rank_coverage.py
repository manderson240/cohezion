"""Item 854: class_severity_rank_coverage() -- fraction of distinct ranks present per class."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_coverage


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_ratio_not_count_primary_discriminator() -> None:
    # class A: INFO(0)+LOW(1)+HIGH(3) -> 3 distinct ranks -> 3/5=0.6; count=3 wrong; distinct_int=3 wrong
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "HIGH")]
    result = class_severity_rank_coverage(problems)
    assert abs(result["A"] - 0.6) < 1e-9


def test_all_five_ranks_gives_one() -> None:
    problems = [_p("B", s) for s in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]
    result = class_severity_rank_coverage(problems)
    assert abs(result["B"] - 1.0) < 1e-9


def test_single_rank_gives_0_2() -> None:
    # Only HIGH(3) -> 1/5 = 0.2
    problems = [_p("C", "HIGH")] * 4
    result = class_severity_rank_coverage(problems)
    assert abs(result["C"] - 0.2) < 1e-9


def test_two_ranks_gives_0_4() -> None:
    problems = [_p("D", "LOW"), _p("D", "LOW"), _p("D", "CRITICAL")]
    result = class_severity_rank_coverage(problems)
    assert abs(result["D"] - 0.4) < 1e-9


def test_four_ranks_gives_0_8() -> None:
    problems = [_p("E", s) for s in ["INFO", "LOW", "MEDIUM", "HIGH"]]
    result = class_severity_rank_coverage(problems)
    assert abs(result["E"] - 0.8) < 1e-9


def test_multiple_classes_independent() -> None:
    problems = [
        _p("X", "INFO"),
        _p("X", "CRITICAL"),  # 2 distinct -> 0.4
        _p("Y", "HIGH"),
    ]  # 1 distinct -> 0.2
    result = class_severity_rank_coverage(problems)
    assert abs(result["X"] - 0.4) < 1e-9
    assert abs(result["Y"] - 0.2) < 1e-9


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_coverage([]) == {}


def test_return_type_is_float() -> None:
    problems = [_p("F", "MEDIUM")]
    result = class_severity_rank_coverage(problems)
    assert isinstance(result["F"], float)


def test_duplicates_do_not_inflate_coverage() -> None:
    # 10 HIGH problems -> still only 1 distinct rank -> 0.2
    problems = [_p("G", "HIGH")] * 10
    result = class_severity_rank_coverage(problems)
    assert abs(result["G"] - 0.2) < 1e-9


def test_coverage_in_0_1_range() -> None:
    problems = [_p("H", "LOW"), _p("H", "HIGH"), _p("H", "CRITICAL")]
    result = class_severity_rank_coverage(problems)
    assert 0.0 < result["H"] <= 1.0
