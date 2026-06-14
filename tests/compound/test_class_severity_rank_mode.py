"""Item 840: class_severity_rank_mode() -- most frequent severity rank per class."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_mode


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_mode_rank_not_count_not_max_primary_discriminator() -> None:
    # class A: INFO(0)*3 + HIGH(3)*2 -> mode rank=0; count=5 wrong; max=3 wrong; mean=6/5 wrong
    problems = [_p("A", "INFO")] * 3 + [_p("A", "HIGH")] * 2
    result = class_severity_rank_mode(problems)
    got = result["A"]
    assert got == 0 and isinstance(got, int) and got != 3 and got != 5


def test_tie_broken_by_lowest_rank() -> None:
    # class B: LOW(1)*2 + HIGH(3)*2 -> tie -> lowest rank=1
    problems = [_p("B", "LOW")] * 2 + [_p("B", "HIGH")] * 2
    result = class_severity_rank_mode(problems)
    assert result["B"] == 1


def test_single_problem_returns_its_rank() -> None:
    problems = [_p("C", "CRITICAL")]
    result = class_severity_rank_mode(problems)
    assert result["C"] == 4


def test_multi_class_independent() -> None:
    problems = [_p("X", "HIGH")] * 5 + [_p("X", "LOW")] * 1 + [_p("Y", "INFO")] * 3
    result = class_severity_rank_mode(problems)
    assert result.get("X") == 3 and result.get("Y") == 0


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_mode([]) == {}
