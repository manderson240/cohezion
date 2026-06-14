"""Item 849: fid_severity_rank_above_threshold() -- count rank > threshold per fid."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_above_threshold


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_strictly_greater_primary_discriminator() -> None:
    # fid f1: 2 HIGH(3) + 1 MEDIUM(2), threshold=2 -> count=2; class-outer wrong; >= wrong
    problems = [_p("A", "f1", "HIGH"), _p("B", "f1", "HIGH"), _p("A", "f1", "MEDIUM")]
    result = fid_severity_rank_above_threshold(problems, 2)
    assert "f1" in result and "A" not in result
    assert result["f1"] == 2


def test_threshold_0_counts_all_non_info() -> None:
    problems = [_p("A", "f2", s) for s in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]
    result = fid_severity_rank_above_threshold(problems, 0)
    assert result["f2"] == 4


def test_threshold_3_counts_critical_only() -> None:
    problems = [_p("A", "f3", "HIGH"), _p("A", "f3", "HIGH"), _p("A", "f3", "CRITICAL")]
    result = fid_severity_rank_above_threshold(problems, 3)
    assert result["f3"] == 1


def test_zero_count_fid_included() -> None:
    problems = [_p("A", "f4", "INFO"), _p("A", "f4", "LOW")]
    result = fid_severity_rank_above_threshold(problems, 2)
    assert "f4" in result and result["f4"] == 0


def test_multiple_fids_independent() -> None:
    problems = [
        _p("X", "f10", "CRITICAL"),
        _p("X", "f10", "CRITICAL"),
        _p("Y", "f11", "LOW"),
        _p("Z", "f12", "HIGH"),
    ]
    result = fid_severity_rank_above_threshold(problems, 2)
    assert result["f10"] == 2
    assert result["f11"] == 0
    assert result["f12"] == 1


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_above_threshold([], 1) == {}


def test_return_type_is_int() -> None:
    problems = [_p("A", "f5", "HIGH")]
    result = fid_severity_rank_above_threshold(problems, 1)
    assert isinstance(result["f5"], int)


def test_threshold_4_returns_all_zeros() -> None:
    problems = [_p("A", "f6", "CRITICAL"), _p("A", "f6", "HIGH")]
    result = fid_severity_rank_above_threshold(problems, 4)
    assert result["f6"] == 0


def test_all_qualifying() -> None:
    problems = [_p("A", "f7", "CRITICAL")] * 4
    result = fid_severity_rank_above_threshold(problems, 2)
    assert result["f7"] == 4


def test_threshold_minus1_counts_all() -> None:
    problems = [_p("A", "f8", "INFO"), _p("A", "f8", "LOW"), _p("A", "f8", "CRITICAL")]
    result = fid_severity_rank_above_threshold(problems, -1)
    assert result["f8"] == 3
