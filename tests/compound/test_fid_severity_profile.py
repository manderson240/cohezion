"""Item 835: fid_severity_profile() -- severity histogram per fid."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_profile


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_severity_profile_primary_discriminator() -> None:
    # fid f1: 2 HIGH + 1 LOW -> {"f1": {"HIGH":2, "LOW":1}}; class-outer wrong
    problems = [_p("A", "f1", "HIGH"), _p("B", "f1", "HIGH"), _p("A", "f1", "LOW")]
    result = fid_severity_profile(problems)
    assert "f1" in result and "A" not in result
    inner = result["f1"]
    assert inner.get("HIGH") == 2 and inner.get("LOW") == 1


def test_absent_severities_not_in_inner_dict() -> None:
    problems = [_p("B", "f2", "CRITICAL")]
    result = fid_severity_profile(problems)
    assert result["f2"].get("CRITICAL") == 1
    assert "HIGH" not in result["f2"]


def test_multiple_fids_independent() -> None:
    problems = [_p("X", "f10", "HIGH"), _p("X", "f10", "HIGH"), _p("Y", "f11", "INFO")]
    result = fid_severity_profile(problems)
    assert result.get("f10", {}).get("HIGH") == 2
    assert result.get("f11", {}).get("INFO") == 1


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_profile([]) == {}


def test_inner_values_are_int() -> None:
    problems = [_p("D", "f99", "HIGH"), _p("D", "f99", "HIGH")]
    result = fid_severity_profile(problems)
    assert isinstance(result["f99"]["HIGH"], int)
