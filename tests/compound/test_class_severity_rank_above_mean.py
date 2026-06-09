"""Item 874: class_severity_rank_above_mean() -- count of problems with rank > class mean."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_above_mean


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_dynamic_mean_not_fixed_threshold_primary_discriminator() -> None:
    # class A: [INFO(0), LOW(1), HIGH(3)] mean=4/3~1.333
    # HIGH(3) > 1.333 -> count=1
    # fixed-threshold=2: count=1 (accidentally right but wrong logic)
    # fixed-threshold=1.0: count=1 (wrong; 2 would satisfy rank>1)
    # All three: count=3 wrong; above-threshold(2): 1 right but different fn
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "HIGH")]
    result = class_severity_rank_above_mean(problems)
    assert result["A"] == 1


def test_all_same_rank_gives_zero() -> None:
    # All HIGH(3): mean=3.0; none strictly > 3 -> count=0
    problems = [_p("B", "HIGH")] * 5
    result = class_severity_rank_above_mean(problems)
    assert result["B"] == 0


def test_single_problem_gives_zero() -> None:
    # Single CRITICAL: mean=4.0; CRITICAL(4) not > 4 -> count=0
    problems = [_p("C", "CRITICAL")]
    result = class_severity_rank_above_mean(problems)
    assert result["C"] == 0


def test_strict_greater_than_not_gte() -> None:
    # [INFO(0), HIGH(3), HIGH(3)]: mean=2.0; HIGH(3) > 2.0 -> count=2
    # >= would still give 2; equality edge on INFO(0): 0 NOT > 2 -> still 0
    # True discriminator: [LOW(1), MEDIUM(2), HIGH(3)]: mean=2.0
    # HIGH(3) > 2.0 -> 1; MEDIUM(2) NOT > 2.0 -> 0; LOW(1) NOT > 2.0 -> 0; count=1
    problems = [_p("D", "LOW"), _p("D", "MEDIUM"), _p("D", "HIGH")]
    result = class_severity_rank_above_mean(problems)
    assert result["D"] == 1


def test_two_problems_above_mean() -> None:
    # [INFO(0), HIGH(3), HIGH(3)]: mean=2.0; both HIGH>2.0 -> count=2
    problems = [_p("E", "INFO"), _p("E", "HIGH"), _p("E", "HIGH")]
    result = class_severity_rank_above_mean(problems)
    assert result["E"] == 2


def test_multiple_classes_independent() -> None:
    # X: [CRITICAL(4), CRITICAL(4), INFO(0)] mean=8/3~2.667; CRITICAL>2.667 -> 2
    # Y: all LOW(1) mean=1.0 -> count=0
    problems = ([_p("X", "CRITICAL"), _p("X", "CRITICAL"), _p("X", "INFO")] +
                [_p("Y", "LOW")] * 4)
    result = class_severity_rank_above_mean(problems)
    assert result["X"] == 2
    assert result["Y"] == 0


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_above_mean([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("F", "HIGH"), _p("F", "LOW")]
    result = class_severity_rank_above_mean(problems)
    assert isinstance(result["F"], int)


def test_all_above_mean_when_bimodal() -> None:
    # [INFO(0), INFO(0), CRITICAL(4), CRITICAL(4)]: mean=2.0
    # CRITICAL(4)>2.0 -> 2; INFO(0) NOT > 2.0 -> count=2
    problems = [_p("G", "INFO"), _p("G", "INFO"),
                _p("G", "CRITICAL"), _p("G", "CRITICAL")]
    result = class_severity_rank_above_mean(problems)
    assert result["G"] == 2


def test_non_integer_mean_threshold() -> None:
    # [LOW(1), LOW(1), HIGH(3)]: mean=5/3~1.667; HIGH(3) > 1.667 -> count=1
    # LOW(1) NOT > 1.667 -> 0; total=1
    problems = [_p("H", "LOW"), _p("H", "LOW"), _p("H", "HIGH")]
    result = class_severity_rank_above_mean(problems)
    assert result["H"] == 1
