"""Item 836: class_severity_rank_std_dev() -- population std dev of severity ranks per class."""
from __future__ import annotations
import math
from cohezion.compound.problem_discovery import Problem, class_severity_rank_std_dev


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_std_not_mad_primary_discriminator() -> None:
    # class A: INFO(0)+LOW(1)+CRITICAL(4) -> mean=5/3
    # std = sqrt(((0-5/3)^2 + (1-5/3)^2 + (4-5/3)^2)/3) ~1.528
    # MAD = (|0-5/3|+|1-5/3|+|4-5/3|)/3 = (5/3+2/3+7/3)/3 = 14/9 ~1.556
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "CRITICAL")]
    result = class_severity_rank_std_dev(problems)
    got = result["A"]
    ranks = [0, 1, 4]
    mean = sum(ranks) / 3
    expected_std = math.sqrt(sum((r - mean) ** 2 for r in ranks) / 3)
    expected_mad = sum(abs(r - mean) for r in ranks) / 3
    assert math.isclose(got, expected_std, abs_tol=1e-9)
    assert not math.isclose(got, expected_mad, abs_tol=1e-4), "Must be std not MAD"
    assert isinstance(got, float)


def test_single_problem_gives_zero() -> None:
    problems = [_p("B", "CRITICAL")]
    result = class_severity_rank_std_dev(problems)
    assert math.isclose(result["B"], 0.0, abs_tol=1e-9)


def test_uniform_severity_gives_zero() -> None:
    problems = [_p("C", "HIGH"), _p("C", "HIGH"), _p("C", "HIGH")]
    result = class_severity_rank_std_dev(problems)
    assert math.isclose(result["C"], 0.0, abs_tol=1e-9)


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_std_dev([]) == {}


def test_return_type_is_float() -> None:
    problems = [_p("D", "HIGH"), _p("D", "LOW")]
    result = class_severity_rank_std_dev(problems)
    assert isinstance(result["D"], float)
