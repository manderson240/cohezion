"""Item 837: fid_severity_rank_std_dev() -- population std dev of severity ranks per fid."""
from __future__ import annotations
import math
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_std_dev


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_std_not_mad_primary_discriminator() -> None:
    # fid f1: INFO(0)+LOW(1)+CRITICAL(4) -> std ~1.528, MAD ~1.556; class-outer wrong
    problems = [_p("A", "f1", "INFO"), _p("A", "f1", "LOW"), _p("B", "f1", "CRITICAL")]
    result = fid_severity_rank_std_dev(problems)
    assert "f1" in result and "A" not in result
    ranks = [0, 1, 4]
    mean = sum(ranks) / 3
    expected_std = math.sqrt(sum((r - mean) ** 2 for r in ranks) / 3)
    assert math.isclose(result["f1"], expected_std, abs_tol=1e-9)


def test_single_problem_gives_zero() -> None:
    problems = [_p("B", "f2", "CRITICAL")]
    result = fid_severity_rank_std_dev(problems)
    assert math.isclose(result["f2"], 0.0, abs_tol=1e-9)


def test_multiple_fids_independent() -> None:
    problems = [_p("X", "f10", "HIGH"), _p("X", "f10", "HIGH"), _p("Y", "f11", "INFO"), _p("Y", "f11", "CRITICAL")]
    result = fid_severity_rank_std_dev(problems)
    assert math.isclose(result.get("f10", -1), 0.0, abs_tol=1e-9)
    expected_f11 = math.sqrt(((0 - 2) ** 2 + (4 - 2) ** 2) / 2)
    assert math.isclose(result.get("f11", -1), expected_f11, abs_tol=1e-9)


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_std_dev([]) == {}


def test_return_type_is_float() -> None:
    problems = [_p("D", "f99", "HIGH"), _p("D", "f99", "LOW")]
    result = fid_severity_rank_std_dev(problems)
    assert isinstance(result["f99"], float)
