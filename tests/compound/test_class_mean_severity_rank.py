"""Item 826: class_mean_severity_rank() -- mean severity rank per class."""

from __future__ import annotations
import math
from cohezion.compound.problem_discovery import Problem, class_mean_severity_rank


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_mean_rank_not_max_not_min_primary_discriminator() -> None:
    # class A: INFO(0)+LOW(1)+HIGH(3) -> mean=4/3=1.333...; max=3 wrong; min=0 wrong
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "HIGH")]
    result = class_mean_severity_rank(problems)
    got = result["A"]
    expected = 4.0 / 3.0
    assert math.isclose(got, expected, abs_tol=1e-9) and isinstance(got, float)
    assert not math.isclose(got, 3.0, abs_tol=1e-6) and not math.isclose(got, 0.0, abs_tol=1e-6)


def test_single_problem_mean_equals_its_rank() -> None:
    problems = [_p("B", "CRITICAL")]
    result = class_mean_severity_rank(problems)
    assert math.isclose(result["B"], 4.0, abs_tol=1e-9)


def test_multi_class_independent() -> None:
    problems = [_p("X", "HIGH"), _p("X", "HIGH"), _p("Y", "INFO"), _p("Y", "CRITICAL")]
    result = class_mean_severity_rank(problems)
    assert math.isclose(result.get("X", -1), 3.0, abs_tol=1e-9)
    assert math.isclose(result.get("Y", -1), 2.0, abs_tol=1e-9)


def test_empty_returns_empty_dict() -> None:
    assert class_mean_severity_rank([]) == {}


def test_return_type_is_float() -> None:
    problems = [_p("D", "HIGH"), _p("D", "LOW")]
    result = class_mean_severity_rank(problems)
    assert isinstance(result["D"], float)
