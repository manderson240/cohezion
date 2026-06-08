"""Item 828: class_severity_rank_spread() -- max minus min severity rank per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_spread


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_spread_not_max_not_mean_primary_discriminator() -> None:
    # class A: INFO(0)+LOW(1)+HIGH(3) -> spread=3-0=3; max=3 wrong; mean=4/3 wrong; min=0 wrong
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "HIGH")]
    result = class_severity_rank_spread(problems)
    got = result["A"]
    assert got == 3 and isinstance(got, int) and got != 0


def test_single_problem_gives_zero_spread() -> None:
    problems = [_p("B", "CRITICAL")]
    result = class_severity_rank_spread(problems)
    assert result["B"] == 0


def test_uniform_severity_gives_zero_spread() -> None:
    problems = [_p("C", "HIGH"), _p("C", "HIGH"), _p("C", "HIGH")]
    result = class_severity_rank_spread(problems)
    assert result["C"] == 0


def test_multi_class_independent() -> None:
    problems = [_p("X", "INFO"), _p("X", "CRITICAL"), _p("Y", "LOW"), _p("Y", "MEDIUM")]
    result = class_severity_rank_spread(problems)
    assert result.get("X") == 4 and result.get("Y") == 1


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_spread([]) == {}
