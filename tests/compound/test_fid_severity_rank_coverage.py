"""Item 855: fid_severity_rank_coverage() -- fraction of distinct ranks present per fid."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_coverage


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_ratio_not_count_primary_discriminator() -> None:
    # fid f1: INFO+LOW+HIGH -> 3 distinct / 5 = 0.6; class-outer wrong; count=3 wrong
    problems = [_p("A", "f1", "INFO"), _p("B", "f1", "LOW"), _p("A", "f1", "HIGH")]
    result = fid_severity_rank_coverage(problems)
    assert "f1" in result and "A" not in result
    assert abs(result["f1"] - 0.6) < 1e-9


def test_all_five_ranks_gives_one() -> None:
    problems = [_p("A", "f2", s) for s in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]
    result = fid_severity_rank_coverage(problems)
    assert abs(result["f2"] - 1.0) < 1e-9


def test_single_rank_gives_0_2() -> None:
    problems = [_p("A", "f3", "CRITICAL")] * 3
    result = fid_severity_rank_coverage(problems)
    assert abs(result["f3"] - 0.2) < 1e-9


def test_two_ranks_gives_0_4() -> None:
    problems = [_p("A", "f4", "INFO"), _p("A", "f4", "HIGH"), _p("A", "f4", "INFO")]
    result = fid_severity_rank_coverage(problems)
    assert abs(result["f4"] - 0.4) < 1e-9


def test_multiple_fids_independent() -> None:
    problems = [_p("X", "f10", "INFO"), _p("X", "f10", "CRITICAL"),  # 2/5=0.4
                _p("Y", "f11", "HIGH")]                               # 1/5=0.2
    result = fid_severity_rank_coverage(problems)
    assert abs(result["f10"] - 0.4) < 1e-9
    assert abs(result["f11"] - 0.2) < 1e-9


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_coverage([]) == {}


def test_return_type_is_float() -> None:
    problems = [_p("A", "f5", "LOW")]
    result = fid_severity_rank_coverage(problems)
    assert isinstance(result["f5"], float)


def test_duplicates_do_not_inflate_coverage() -> None:
    problems = [_p("A", "f6", "MEDIUM")] * 8
    result = fid_severity_rank_coverage(problems)
    assert abs(result["f6"] - 0.2) < 1e-9


def test_four_ranks_gives_0_8() -> None:
    problems = [_p("A", "f7", s) for s in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]]
    result = fid_severity_rank_coverage(problems)
    assert abs(result["f7"] - 0.8) < 1e-9


def test_coverage_in_0_1_range() -> None:
    problems = [_p("A", "f8", "HIGH"), _p("A", "f8", "CRITICAL")]
    result = fid_severity_rank_coverage(problems)
    assert 0.0 < result["f8"] <= 1.0
