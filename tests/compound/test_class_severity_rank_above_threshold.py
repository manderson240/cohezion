"""Item 848: class_severity_rank_above_threshold() -- count rank > threshold per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_above_threshold


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_strictly_greater_not_gte_primary_discriminator() -> None:
    # class A: 2 HIGH(3) + 1 MEDIUM(2), threshold=2
    # strictly > 2: HIGH counts (rank=3), MEDIUM does NOT (rank=2)
    # >= impl would return 3 (wrong); strictly > returns 2
    problems = [_p("A", "HIGH"), _p("A", "HIGH"), _p("A", "MEDIUM")]
    result = class_severity_rank_above_threshold(problems, 2)
    assert result["A"] == 2


def test_threshold_0_counts_all_above_info() -> None:
    # INFO(0) excluded; LOW(1)+MEDIUM(2)+HIGH(3)+CRITICAL(4) all > 0
    problems = [_p("B", "INFO"), _p("B", "LOW"), _p("B", "MEDIUM"), _p("B", "HIGH"), _p("B", "CRITICAL")]
    result = class_severity_rank_above_threshold(problems, 0)
    assert result["B"] == 4


def test_threshold_3_counts_critical_only() -> None:
    # Only CRITICAL(4) > 3; HIGH(3) does NOT qualify
    problems = [_p("C", "HIGH"), _p("C", "HIGH"), _p("C", "CRITICAL")]
    result = class_severity_rank_above_threshold(problems, 3)
    assert result["C"] == 1


def test_zero_count_class_included() -> None:
    # class D has no problems above threshold — still present with count=0
    problems = [_p("D", "INFO"), _p("D", "LOW")]
    result = class_severity_rank_above_threshold(problems, 2)
    assert "D" in result and result["D"] == 0


def test_multiple_classes_independent() -> None:
    # A: 2 CRITICAL(4) > 2; B: 1 LOW(1) > 2 -> 0; C: 1 HIGH(3) > 2 -> 1
    problems = [_p("A", "CRITICAL"), _p("A", "CRITICAL"), _p("B", "LOW"), _p("C", "HIGH")]
    result = class_severity_rank_above_threshold(problems, 2)
    assert result["A"] == 2
    assert result["B"] == 0
    assert result["C"] == 1


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_above_threshold([], 2) == {}


def test_return_type_is_int() -> None:
    problems = [_p("E", "HIGH")]
    result = class_severity_rank_above_threshold(problems, 1)
    assert isinstance(result["E"], int)


def test_threshold_4_returns_all_zeros() -> None:
    # Nothing has rank > 4 (CRITICAL=4 is max)
    problems = [_p("F", "CRITICAL"), _p("F", "HIGH")]
    result = class_severity_rank_above_threshold(problems, 4)
    assert result["F"] == 0


def test_threshold_minus1_counts_all() -> None:
    # Every rank > -1, so all problems qualify
    problems = [_p("G", "INFO"), _p("G", "LOW"), _p("G", "CRITICAL")]
    result = class_severity_rank_above_threshold(problems, -1)
    assert result["G"] == 3


def test_all_qualifying_counts_all() -> None:
    problems = [_p("H", "CRITICAL")] * 5
    result = class_severity_rank_above_threshold(problems, 2)
    assert result["H"] == 5
