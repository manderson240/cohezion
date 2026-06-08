"""Item 824: class_min_severity_rank() -- minimum severity rank per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_min_severity_rank


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_min_rank_not_max_not_mean_primary_discriminator() -> None:
    # class A has INFO(0), LOW(1), HIGH(3) -> min rank = 0; max=3 wrong; mean=4/3 wrong
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "HIGH")]
    result = class_min_severity_rank(problems)
    got = result["A"]
    assert got == 0 and isinstance(got, int) and got != 3


def test_single_critical_returns_four() -> None:
    problems = [_p("B", "CRITICAL")]
    result = class_min_severity_rank(problems)
    assert result["B"] == 4


def test_multi_class_independent() -> None:
    problems = [_p("X", "MEDIUM"), _p("X", "LOW"), _p("Y", "INFO"), _p("Y", "CRITICAL")]
    result = class_min_severity_rank(problems)
    assert result.get("X") == 1 and result.get("Y") == 0


def test_empty_returns_empty_dict() -> None:
    assert class_min_severity_rank([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("D", "HIGH"), _p("D", "LOW")]
    result = class_min_severity_rank(problems)
    assert isinstance(result["D"], int)
