"""Item 850: class_severity_rank_at_or_below_threshold() -- count rank <= threshold per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_at_or_below_threshold


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_at_or_below_not_strictly_below_primary_discriminator() -> None:
    # class A: INFO(0)+LOW(1)+MEDIUM(2), threshold=1
    # at-or-below (<=1): INFO+LOW=2; strictly-<1 returns 1 (INFO only) wrong
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "MEDIUM")]
    result = class_severity_rank_at_or_below_threshold(problems, 1)
    assert result["A"] == 2


def test_threshold_4_counts_all() -> None:
    # All ranks <= 4; all 5 problems qualify
    problems = [_p("B", s) for s in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]
    result = class_severity_rank_at_or_below_threshold(problems, 4)
    assert result["B"] == 5


def test_threshold_0_counts_info_only() -> None:
    # Only INFO(0) <= 0
    problems = [_p("C", "INFO"), _p("C", "LOW"), _p("C", "HIGH")]
    result = class_severity_rank_at_or_below_threshold(problems, 0)
    assert result["C"] == 1


def test_zero_count_class_included() -> None:
    # class D has no problems at-or-below threshold=0 (only HIGH/CRITICAL)
    problems = [_p("D", "HIGH"), _p("D", "CRITICAL")]
    result = class_severity_rank_at_or_below_threshold(problems, 0)
    assert "D" in result and result["D"] == 0


def test_multiple_classes_independent() -> None:
    problems = [
        _p("A", "INFO"), _p("A", "LOW"),   # A: 2 <= 2
        _p("B", "HIGH"), _p("B", "CRITICAL"),  # B: 0 <= 2
        _p("C", "MEDIUM"),               # C: 1 <= 2
    ]
    result = class_severity_rank_at_or_below_threshold(problems, 2)
    assert result["A"] == 2
    assert result["B"] == 0
    assert result["C"] == 1


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_at_or_below_threshold([], 2) == {}


def test_return_type_is_int() -> None:
    problems = [_p("E", "LOW")]
    result = class_severity_rank_at_or_below_threshold(problems, 1)
    assert isinstance(result["E"], int)


def test_threshold_minus1_returns_all_zeros() -> None:
    # No rank can be <= -1 (min rank is 0=INFO)
    problems = [_p("F", "INFO"), _p("F", "CRITICAL")]
    result = class_severity_rank_at_or_below_threshold(problems, -1)
    assert result["F"] == 0


def test_all_qualifying() -> None:
    problems = [_p("G", "INFO")] * 5
    result = class_severity_rank_at_or_below_threshold(problems, 2)
    assert result["G"] == 5


def test_threshold_2_counts_low_medium_info() -> None:
    # INFO(0)+LOW(1)+MEDIUM(2) all <= 2; HIGH(3) excluded
    problems = [_p("H", "INFO"), _p("H", "LOW"), _p("H", "MEDIUM"), _p("H", "HIGH")]
    result = class_severity_rank_at_or_below_threshold(problems, 2)
    assert result["H"] == 3
