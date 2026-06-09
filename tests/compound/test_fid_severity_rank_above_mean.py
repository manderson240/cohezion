"""Item 875: fid_severity_rank_above_mean() -- count of problems with rank > fid mean."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_above_mean


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_outer_key_fid_not_class_primary_discriminator() -> None:
    # keyed by fid; class-keyed impl is wrong
    problems = [_p("A", "f1", "INFO"), _p("A", "f1", "HIGH")]
    result = fid_severity_rank_above_mean(problems)
    assert "f1" in result
    assert "A" not in result


def test_dynamic_mean_threshold() -> None:
    # fid f2: [INFO(0), LOW(1), HIGH(3)] mean=4/3~1.333; HIGH(3)>1.333 -> 1
    problems = [_p("A", "f2", "INFO"), _p("A", "f2", "LOW"), _p("A", "f2", "HIGH")]
    result = fid_severity_rank_above_mean(problems)
    assert result["f2"] == 1


def test_all_same_rank_gives_zero() -> None:
    problems = [_p("B", "f3", "MEDIUM")] * 3
    result = fid_severity_rank_above_mean(problems)
    assert result["f3"] == 0


def test_single_problem_gives_zero() -> None:
    problems = [_p("C", "f4", "CRITICAL")]
    result = fid_severity_rank_above_mean(problems)
    assert result["f4"] == 0


def test_strict_greater_not_gte() -> None:
    # fid f5: [LOW(1), MEDIUM(2), HIGH(3)]: mean=2.0; HIGH>2.0 -> count=1
    # MEDIUM(2) NOT strictly > 2.0 -> 0
    problems = [_p("D", "f5", "LOW"), _p("D", "f5", "MEDIUM"), _p("D", "f5", "HIGH")]
    result = fid_severity_rank_above_mean(problems)
    assert result["f5"] == 1


def test_class_irrelevant_same_fid() -> None:
    # different classes but same fid -> grouped by fid
    problems = [_p("X", "f6", "INFO"), _p("Y", "f6", "CRITICAL")]
    # mean=2.0; CRITICAL(4)>2.0 -> 1
    result = fid_severity_rank_above_mean(problems)
    assert result["f6"] == 1


def test_multiple_fids_independent() -> None:
    # f7: all HIGH -> count=0; f8: [INFO,CRITICAL] -> CRITICAL>mean=2 -> 1
    problems = ([_p("A", "f7", "HIGH")] * 3 +
                [_p("B", "f8", "INFO"), _p("B", "f8", "CRITICAL")])
    result = fid_severity_rank_above_mean(problems)
    assert result["f7"] == 0
    assert result["f8"] == 1


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_above_mean([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("G", "f9", "HIGH"), _p("G", "f9", "LOW")]
    result = fid_severity_rank_above_mean(problems)
    assert isinstance(result["f9"], int)


def test_majority_above_mean() -> None:
    # fid f10: [LOW(1), HIGH(3), HIGH(3), CRITICAL(4)] mean=11/4=2.75
    # HIGH(3)>2.75 -> 2; CRITICAL(4)>2.75 -> 1; total=3
    problems = [_p("H", "f10", "LOW"), _p("H", "f10", "HIGH"),
                _p("H", "f10", "HIGH"), _p("H", "f10", "CRITICAL")]
    result = fid_severity_rank_above_mean(problems)
    assert result["f10"] == 3
