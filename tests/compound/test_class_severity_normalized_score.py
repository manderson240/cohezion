"""Item 846: class_severity_normalized_score() -- mean severity rank / 4.0 per class."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_normalized_score


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_normalized_not_raw_mean_primary_discriminator() -> None:
    # class A: [HIGH(3),CRITICAL(4)] -> mean=3.5 -> normalized=3.5/4=0.875
    # raw mean=3.5 would be wrong; count=2 wrong; sum=7 wrong
    problems = [_p("A", "HIGH"), _p("A", "CRITICAL")]
    result = class_severity_normalized_score(problems)
    assert abs(result["A"] - 0.875) < 1e-9
    assert isinstance(result["A"], float)


def test_all_critical_gives_one() -> None:
    problems = [_p("A", "CRITICAL"), _p("A", "CRITICAL")]
    result = class_severity_normalized_score(problems)
    assert abs(result["A"] - 1.0) < 1e-9


def test_all_info_gives_zero() -> None:
    problems = [_p("B", "INFO"), _p("B", "INFO")]
    result = class_severity_normalized_score(problems)
    assert abs(result["B"] - 0.0) < 1e-9


def test_empty_returns_empty_dict() -> None:
    assert class_severity_normalized_score([]) == {}


def test_multi_class_independent() -> None:
    # A: LOW(1) -> 1/4=0.25; B: HIGH(3) -> 3/4=0.75
    problems = [_p("A", "LOW"), _p("B", "HIGH")]
    result = class_severity_normalized_score(problems)
    assert abs(result["A"] - 0.25) < 1e-9
    assert abs(result["B"] - 0.75) < 1e-9
