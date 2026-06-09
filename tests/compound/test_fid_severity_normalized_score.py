"""Item 847: fid_severity_normalized_score() -- mean severity rank / 4.0 per fid (fid-axis complement of 846)."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_normalized_score


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="C", finding_id=fid, severity=sev)


def test_fid_axis_not_class_primary_discriminator() -> None:
    # fid f1: [HIGH(3),CRITICAL(4)] -> mean=3.5 -> normalized=0.875; class-outer wrong
    problems = [_p("f1", "HIGH"), _p("f1", "CRITICAL")]
    result = fid_severity_normalized_score(problems)
    assert abs(result["f1"] - 0.875) < 1e-9
    assert isinstance(result["f1"], float)


def test_all_critical_gives_one() -> None:
    problems = [_p("f2", "CRITICAL"), _p("f2", "CRITICAL")]
    result = fid_severity_normalized_score(problems)
    assert abs(result["f2"] - 1.0) < 1e-9


def test_all_info_gives_zero() -> None:
    problems = [_p("f3", "INFO"), _p("f3", "INFO")]
    result = fid_severity_normalized_score(problems)
    assert abs(result["f3"] - 0.0) < 1e-9


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_normalized_score([]) == {}


def test_multi_fid_independent() -> None:
    # f1: LOW(1) -> 0.25; f2: HIGH(3) -> 0.75
    problems = [_p("f1", "LOW"), _p("f2", "HIGH")]
    result = fid_severity_normalized_score(problems)
    assert abs(result["f1"] - 0.25) < 1e-9
    assert abs(result["f2"] - 0.75) < 1e-9
