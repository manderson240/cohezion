"""Item 827: fid_mean_severity_rank() -- mean severity rank per fid."""

from __future__ import annotations
import math
from cohezion.compound.problem_discovery import Problem, fid_mean_severity_rank


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_mean_rank_primary_discriminator() -> None:
    # fid f1: INFO(0)+LOW(1)+HIGH(3) -> mean=4/3; class-outer wrong; max=3 wrong
    problems = [_p("A", "f1", "INFO"), _p("A", "f1", "LOW"), _p("B", "f1", "HIGH")]
    result = fid_mean_severity_rank(problems)
    assert "f1" in result and "A" not in result
    assert math.isclose(result["f1"], 4.0 / 3.0, abs_tol=1e-9)


def test_single_problem_mean_equals_its_rank() -> None:
    problems = [_p("B", "f2", "CRITICAL")]
    result = fid_mean_severity_rank(problems)
    assert math.isclose(result["f2"], 4.0, abs_tol=1e-9)


def test_multiple_fids_independent() -> None:
    problems = [
        _p("X", "f10", "HIGH"),
        _p("X", "f10", "HIGH"),
        _p("Y", "f11", "INFO"),
        _p("Y", "f11", "CRITICAL"),
    ]
    result = fid_mean_severity_rank(problems)
    assert math.isclose(result.get("f10", -1), 3.0, abs_tol=1e-9)
    assert math.isclose(result.get("f11", -1), 2.0, abs_tol=1e-9)


def test_empty_returns_empty_dict() -> None:
    assert fid_mean_severity_rank([]) == {}


def test_return_type_is_float() -> None:
    problems = [_p("D", "f99", "HIGH"), _p("D", "f99", "LOW")]
    result = fid_mean_severity_rank(problems)
    assert isinstance(result["f99"], float)
