"""Item 844: class_weighted_severity_score() -- sum of severity ranks per class."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_weighted_severity_score


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_sum_not_count_not_mean_primary_discriminator() -> None:
    # class A: INFO(0)+LOW(1)+HIGH(3) -> sum=4; count=3 wrong; mean=4/3 wrong; max=3 wrong
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "HIGH")]
    result = class_weighted_severity_score(problems)
    got = result["A"]
    assert got == 4 and isinstance(got, int) and got != 3


def test_all_info_gives_zero_score() -> None:
    problems = [_p("B", "INFO")] * 5
    result = class_weighted_severity_score(problems)
    assert result["B"] == 0


def test_multi_class_independent() -> None:
    problems = [_p("X", "CRITICAL")] * 2 + [_p("Y", "LOW")] * 3
    result = class_weighted_severity_score(problems)
    assert result.get("X") == 8 and result.get("Y") == 3


def test_empty_returns_empty_dict() -> None:
    assert class_weighted_severity_score([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("D", "HIGH"), _p("D", "LOW")]
    result = class_weighted_severity_score(problems)
    assert isinstance(result["D"], int)
