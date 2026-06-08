"""Item 815: fid_severity_rank_high_only_count() -- count rank==3 (HIGH only) per fid."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_high_only_count

def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)

def test_fid_outer_high_only_count_primary_discriminator() -> None:
    problems = [_p("A", "f1", "HIGH")] * 3 + [_p("A", "f1", "CRITICAL")] * 2 + [_p("B", "f2", "HIGH")] * 1
    result = fid_severity_rank_high_only_count(problems)
    assert "f1" in result and "A" not in result
    assert result["f1"] == 3 and result["f2"] == 1

def test_critical_only_gives_zero_not_excluded() -> None:
    problems = [_p("B", "f3", "CRITICAL")] * 4
    result = fid_severity_rank_high_only_count(problems)
    assert "f3" in result and result["f3"] == 0

def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_high_only_count([]) == {}

def test_multiple_fids_independent() -> None:
    problems = [_p("X", "f10", "HIGH")] * 4 + [_p("X", "f11", "CRITICAL")] * 3 + [_p("Y", "f12", "HIGH")] * 2
    result = fid_severity_rank_high_only_count(problems)
    assert result.get("f10") == 4 and result.get("f11") == 0 and result.get("f12") == 2

def test_return_type_is_int() -> None:
    problems = [_p("D", "f99", "HIGH"), _p("D", "f99", "CRITICAL")]
    result = fid_severity_rank_high_only_count(problems)
    assert isinstance(result["f99"], int)
