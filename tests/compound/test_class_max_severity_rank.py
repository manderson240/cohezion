"""Item 822: class_max_severity_rank() -- maximum severity rank per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_max_severity_rank


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_max_rank_not_label_not_mean_primary_discriminator() -> None:
    # class A has INFO(0), LOW(1), HIGH(3) -> max rank = 3; mean = 4/3 wrong; label "HIGH" wrong
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "HIGH")]
    result = class_max_severity_rank(problems)
    got = result["A"]
    assert got == 3 and isinstance(got, int)


def test_single_problem_returns_its_rank() -> None:
    problems = [_p("B", "CRITICAL")]
    result = class_max_severity_rank(problems)
    assert result["B"] == 4


def test_multi_class_independent() -> None:
    problems = [_p("X", "MEDIUM"), _p("X", "LOW"), _p("Y", "INFO"), _p("Y", "CRITICAL")]
    result = class_max_severity_rank(problems)
    assert result.get("X") == 2 and result.get("Y") == 4


def test_empty_returns_empty_dict() -> None:
    assert class_max_severity_rank([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("D", "HIGH"), _p("D", "LOW")]
    result = class_max_severity_rank(problems)
    assert isinstance(result["D"], int)
