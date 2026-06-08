"""Item 821: fid_severity_rank_info_only_count() -- count rank==0 (INFO only) per fid."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_info_only_count


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_info_only_count_primary_discriminator() -> None:
    problems = [_p("A", "f1", "INFO")] * 3 + [_p("A", "f1", "LOW")] * 2 + [_p("B", "f2", "INFO")] * 1
    result = fid_severity_rank_info_only_count(problems)
    assert "f1" in result and "A" not in result
    assert result["f1"] == 3 and result["f2"] == 1


def test_low_only_gives_zero_not_excluded() -> None:
    problems = [_p("B", "f3", "LOW")] * 4
    result = fid_severity_rank_info_only_count(problems)
    assert "f3" in result and result["f3"] == 0


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_info_only_count([]) == {}


def test_multiple_fids_independent() -> None:
    problems = [_p("X", "f10", "INFO")] * 4 + [_p("X", "f11", "LOW")] * 3 + [_p("Y", "f12", "INFO")] * 2
    result = fid_severity_rank_info_only_count(problems)
    assert result.get("f10") == 4 and result.get("f11") == 0 and result.get("f12") == 2


def test_return_type_is_int() -> None:
    problems = [_p("D", "f99", "INFO"), _p("D", "f99", "LOW")]
    result = fid_severity_rank_info_only_count(problems)
    assert isinstance(result["f99"], int)
