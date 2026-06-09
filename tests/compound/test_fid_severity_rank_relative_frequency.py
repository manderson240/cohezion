"""Item 863: fid_severity_rank_relative_frequency() -- fraction per rank per fid."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_relative_frequency


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_two_level_float_primary_discriminator() -> None:
    # fid f1: 2 HIGH(3)+2 LOW(1)+1 INFO(0) -> {3:0.4, 1:0.4, 0:0.2}; class-outer wrong; count wrong
    problems = [_p("A", "f1", "HIGH"), _p("B", "f1", "HIGH"),
                _p("A", "f1", "LOW"), _p("B", "f1", "LOW"),
                _p("A", "f1", "INFO")]
    result = fid_severity_rank_relative_frequency(problems)
    assert "f1" in result and "A" not in result
    assert abs(result["f1"][3] - 0.4) < 1e-9
    assert abs(result["f1"][1] - 0.4) < 1e-9
    assert abs(result["f1"][0] - 0.2) < 1e-9


def test_fractions_sum_to_one() -> None:
    problems = [_p("A", "f2", s) for s in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]
    result = fid_severity_rank_relative_frequency(problems)
    assert abs(sum(result["f2"].values()) - 1.0) < 1e-9


def test_single_rank_gives_one() -> None:
    problems = [_p("A", "f3", "CRITICAL")] * 3
    result = fid_severity_rank_relative_frequency(problems)
    assert abs(result["f3"][4] - 1.0) < 1e-9
    assert len(result["f3"]) == 1


def test_two_ranks_equal_gives_half() -> None:
    problems = [_p("A", "f4", "HIGH"), _p("A", "f4", "LOW")]
    result = fid_severity_rank_relative_frequency(problems)
    assert abs(result["f4"][3] - 0.5) < 1e-9
    assert abs(result["f4"][1] - 0.5) < 1e-9


def test_multiple_fids_independent() -> None:
    problems = [_p("X", "f10", "CRITICAL"), _p("X", "f10", "CRITICAL"),
                _p("Y", "f11", "HIGH"), _p("Y", "f11", "LOW")]
    result = fid_severity_rank_relative_frequency(problems)
    assert abs(result["f10"][4] - 1.0) < 1e-9
    assert abs(result["f11"][3] - 0.5) < 1e-9


def test_return_type_is_float() -> None:
    problems = [_p("A", "f5", "LOW"), _p("A", "f5", "HIGH")]
    result = fid_severity_rank_relative_frequency(problems)
    assert isinstance(result["f5"][1], float)


def test_outer_key_is_fid_inner_key_is_int() -> None:
    problems = [_p("A", "f6", "MEDIUM")]
    result = fid_severity_rank_relative_frequency(problems)
    assert "f6" in result
    assert isinstance(list(result["f6"].keys())[0], int)


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_relative_frequency([]) == {}


def test_absent_ranks_not_included() -> None:
    problems = [_p("A", "f7", "LOW")] * 4
    result = fid_severity_rank_relative_frequency(problems)
    assert set(result["f7"].keys()) == {1}


def test_three_equal_thirds() -> None:
    problems = [_p("A", "f8", s) for s in ["INFO", "MEDIUM", "CRITICAL"]]
    result = fid_severity_rank_relative_frequency(problems)
    for rank in [0, 2, 4]:
        assert abs(result["f8"][rank] - 1.0 / 3.0) < 1e-9
