"""Item 872: class_severity_rank_z_scores() -- per-problem z-score within class."""
from __future__ import annotations
import math
from cohezion.compound.problem_discovery import Problem, class_severity_rank_z_scores


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_list_not_aggregate_primary_discriminator() -> None:
    # class A: [INFO(0), HIGH(3), HIGH(3)]
    # mean=2.0, std=sqrt(2)~1.4142
    # z-scores: [(0-2)/sqrt(2), (3-2)/sqrt(2), (3-2)/sqrt(2)]
    # = [-sqrt(2), 1/sqrt(2), 1/sqrt(2)]
    problems = [_p("A", "INFO"), _p("A", "HIGH"), _p("A", "HIGH")]
    result = class_severity_rank_z_scores(problems)
    expected = [
        (0 - 2.0) / math.sqrt(2),
        (3 - 2.0) / math.sqrt(2),
        (3 - 2.0) / math.sqrt(2),
    ]
    assert len(result["A"]) == 3
    for got, exp in zip(result["A"], expected):
        assert abs(got - exp) < 1e-9


def test_std_zero_gives_all_zeros() -> None:
    # All HIGH(3): mean=3, std=0 -> all z-scores = 0.0
    problems = [_p("B", "HIGH")] * 4
    result = class_severity_rank_z_scores(problems)
    assert all(abs(z) < 1e-9 for z in result["B"])
    assert len(result["B"]) == 4


def test_single_problem_gives_single_zero() -> None:
    # Single problem: std=0 -> z=0.0
    problems = [_p("C", "CRITICAL")]
    result = class_severity_rank_z_scores(problems)
    assert len(result["C"]) == 1
    assert abs(result["C"][0]) < 1e-9


def test_order_preserved() -> None:
    # Order of z-scores matches input order
    problems = [_p("D", "INFO"), _p("D", "CRITICAL")]
    # mean=2.0, std=2.0 -> z = [-1.0, 1.0]
    result = class_severity_rank_z_scores(problems)
    assert result["D"][0] < 0  # INFO -> negative z
    assert result["D"][1] > 0  # CRITICAL -> positive z
    assert abs(result["D"][0] + result["D"][1]) < 1e-9  # symmetric around mean


def test_z_scores_sum_to_zero() -> None:
    # Sum of z-scores must always equal 0 (math identity)
    problems = [_p("E", "INFO"), _p("E", "LOW"), _p("E", "MEDIUM"),
                _p("E", "HIGH"), _p("E", "CRITICAL")]
    result = class_severity_rank_z_scores(problems)
    assert abs(sum(result["E"])) < 1e-9


def test_return_type_is_float_list() -> None:
    problems = [_p("F", "HIGH"), _p("F", "LOW")]
    result = class_severity_rank_z_scores(problems)
    assert isinstance(result["F"], list)
    assert all(isinstance(z, float) for z in result["F"])


def test_multiple_classes_independent() -> None:
    # X: [INFO,HIGH] -> symmetric; Y: all MEDIUM -> all zeros
    problems = ([_p("X", "INFO"), _p("X", "HIGH")] +
                [_p("Y", "MEDIUM")] * 3)
    result = class_severity_rank_z_scores(problems)
    assert len(result["X"]) == 2
    assert abs(result["X"][0] + result["X"][1]) < 1e-9  # sum=0
    assert all(abs(z) < 1e-9 for z in result["Y"])      # all zero


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_z_scores([]) == {}


def test_two_problems_opposite_extremes() -> None:
    # [INFO(0), CRITICAL(4)]: mean=2.0, std=2.0 -> z=[-1.0, 1.0]
    problems = [_p("G", "INFO"), _p("G", "CRITICAL")]
    result = class_severity_rank_z_scores(problems)
    assert abs(result["G"][0] - (-1.0)) < 1e-9
    assert abs(result["G"][1] - 1.0) < 1e-9


def test_high_severity_gives_positive_z() -> None:
    # If CRITICAL is the max in a mixed class, its z-score > 0
    problems = [_p("H", "LOW"), _p("H", "LOW"), _p("H", "CRITICAL")]
    result = class_severity_rank_z_scores(problems)
    assert result["H"][2] > 0   # CRITICAL has positive z
    assert result["H"][0] < 0   # LOW has negative z
