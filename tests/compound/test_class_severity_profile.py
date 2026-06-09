"""Item 834: class_severity_profile() -- severity histogram per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_profile


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_two_level_dict_not_flat_primary_discriminator() -> None:
    # class A: 2 HIGH + 1 LOW -> {"A": {"HIGH":2, "LOW":1}}; flat single-axis wrong
    problems = [_p("A", "HIGH"), _p("A", "HIGH"), _p("A", "LOW")]
    result = class_severity_profile(problems)
    assert "A" in result
    inner = result["A"]
    assert inner.get("HIGH") == 2 and inner.get("LOW") == 1


def test_absent_severities_not_in_inner_dict() -> None:
    problems = [_p("B", "CRITICAL")]
    result = class_severity_profile(problems)
    assert result["B"].get("CRITICAL") == 1
    assert "HIGH" not in result["B"]


def test_multi_class_independent() -> None:
    problems = [_p("X", "HIGH"), _p("X", "HIGH"), _p("Y", "INFO"), _p("Y", "CRITICAL")]
    result = class_severity_profile(problems)
    assert result.get("X", {}).get("HIGH") == 2
    assert result.get("Y", {}).get("INFO") == 1 and result.get("Y", {}).get("CRITICAL") == 1


def test_empty_returns_empty_dict() -> None:
    assert class_severity_profile([]) == {}


def test_inner_values_are_int() -> None:
    problems = [_p("D", "HIGH"), _p("D", "HIGH")]
    result = class_severity_profile(problems)
    assert isinstance(result["D"]["HIGH"], int)
