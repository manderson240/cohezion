"""Item 876: class_severity_rank_below_mean() -- count below dynamic mean per class."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_below_mean


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_below_not_above_primary_discriminator() -> None:
    # class A: [INFO(0),LOW(1),HIGH(3)] mean=4/3~1.333
    # INFO(0)<1.333 -> YES; LOW(1)<1.333 -> YES; HIGH(3)<1.333 -> NO -> count=2
    # above_mean impl gives HIGH>mean=1 (wrong direction kills it here too: above gives 1, below gives 2)
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "HIGH")]
    result = class_severity_rank_below_mean(problems)
    assert result["A"] == 2  # INFO(0) and LOW(1) are both below mean 1.333


def test_all_same_rank_gives_zero() -> None:
    problems = [_p("B", "HIGH")] * 4
    result = class_severity_rank_below_mean(problems)
    assert result["B"] == 0


def test_single_problem_gives_zero() -> None:
    problems = [_p("C", "CRITICAL")]
    result = class_severity_rank_below_mean(problems)
    assert result["C"] == 0


def test_all_below_except_one() -> None:
    # [INFO*4, CRITICAL(4)] mean=0.8 -> INFO(0)<0.8 -> count=4; CRITICAL=4>0.8 above
    problems = [_p("D", "INFO")] * 4 + [_p("D", "CRITICAL")]
    result = class_severity_rank_below_mean(problems)
    assert result["D"] == 4


def test_symmetric_dist_balanced() -> None:
    # [INFO(0), CRITICAL(4)] mean=2.0 -> both exactly 2.0 away; 0<2 -> count=1; 4>2 -> count above=1
    problems = [_p("E", "INFO"), _p("E", "CRITICAL")]
    result = class_severity_rank_below_mean(problems)
    assert result["E"] == 1  # INFO is below mean


def test_multiple_classes_independent() -> None:
    # X: [HIGH,HIGH] -> all zero; Y: [INFO,HIGH] mean=1.5 -> INFO(0)<1.5 count=1
    problems = [_p("X", "HIGH"), _p("X", "HIGH")] + [_p("Y", "INFO"), _p("Y", "HIGH")]
    result = class_severity_rank_below_mean(problems)
    assert result["X"] == 0
    assert result["Y"] == 1


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_below_mean([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("F", "HIGH"), _p("F", "LOW")]
    result = class_severity_rank_below_mean(problems)
    assert isinstance(result["F"], int)


def test_three_below_two_above() -> None:
    # [INFO(0)*3, HIGH(3), CRITICAL(4)] mean=7/5=1.4 -> INFO(0)<1.4 count=3
    problems = [_p("G", "INFO")] * 3 + [_p("G", "HIGH"), _p("G", "CRITICAL")]
    result = class_severity_rank_below_mean(problems)
    assert result["G"] == 3


def test_at_exactly_mean_not_counted() -> None:
    # [LOW(1), LOW(1), HIGH(3)] mean=5/3~1.667 -> LOW(1)<1.667 -> count=2
    # STRICT less-than: rank=mean is NOT below
    problems = [_p("H", "LOW"), _p("H", "LOW"), _p("H", "HIGH")]
    result = class_severity_rank_below_mean(problems)
    assert result["H"] == 2
