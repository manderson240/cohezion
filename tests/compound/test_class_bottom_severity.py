"""Item 866: class_bottom_severity() -- least severe problem severity label per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_bottom_severity


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_min_label_not_max_primary_discriminator() -> None:
    # class A: [INFO, LOW, HIGH] -> "INFO" (min rank 0)
    # class_top_severity returns "HIGH" (wrong); int-impl returns 0 (wrong)
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "HIGH")]
    result = class_bottom_severity(problems)
    assert result["A"] == "INFO"


def test_single_problem_returns_its_severity() -> None:
    problems = [_p("B", "CRITICAL")]
    result = class_bottom_severity(problems)
    assert result["B"] == "CRITICAL"


def test_all_same_severity_returns_that_severity() -> None:
    problems = [_p("C", "MEDIUM")] * 5
    result = class_bottom_severity(problems)
    assert result["C"] == "MEDIUM"


def test_high_count_does_not_override_single_info() -> None:
    # 5 HIGH + 1 INFO -> "INFO" (INFO rank 0 < HIGH rank 3)
    problems = [_p("D", "HIGH")] * 5 + [_p("D", "INFO")]
    result = class_bottom_severity(problems)
    assert result["D"] == "INFO"


def test_low_beats_medium() -> None:
    problems = [_p("E", "MEDIUM"), _p("E", "MEDIUM"), _p("E", "LOW")]
    result = class_bottom_severity(problems)
    assert result["E"] == "LOW"


def test_critical_only_returns_critical() -> None:
    problems = [_p("F", "CRITICAL")] * 3
    result = class_bottom_severity(problems)
    assert result["F"] == "CRITICAL"


def test_multiple_classes_independent() -> None:
    # X: [HIGH, HIGH, LOW] -> "LOW"; Y: [CRITICAL, MEDIUM] -> "MEDIUM"
    problems = ([_p("X", "HIGH"), _p("X", "HIGH"), _p("X", "LOW")] +
                [_p("Y", "CRITICAL"), _p("Y", "MEDIUM")])
    result = class_bottom_severity(problems)
    assert result["X"] == "LOW"
    assert result["Y"] == "MEDIUM"


def test_empty_returns_empty_dict() -> None:
    assert class_bottom_severity([]) == {}


def test_return_type_is_str() -> None:
    problems = [_p("G", "HIGH")]
    result = class_bottom_severity(problems)
    assert isinstance(result["G"], str)


def test_info_is_lowest_across_all_ranks() -> None:
    # INFO is rank 0 — lowest; all five ranks present -> "INFO"
    problems = [_p("H", s) for s in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]
    result = class_bottom_severity(problems)
    assert result["H"] == "INFO"
