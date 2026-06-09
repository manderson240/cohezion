"""Item 877: fid_severity_rank_below_mean() -- count below dynamic mean per fid."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_below_mean


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_below_not_above_primary_discriminator() -> None:
    # fid f1: [INFO(0),LOW(1),HIGH(3)] mean=4/3~1.333
    # INFO(0)<1.333 YES; LOW(1)<1.333 YES; HIGH(3)<1.333 NO -> count=2
    # class-outer wrong; above-impl wrong direction (above gives 1, below gives 2)
    problems = [_p("A", "f1", "INFO"), _p("A", "f1", "LOW"), _p("A", "f1", "HIGH")]
    result = fid_severity_rank_below_mean(problems)
    assert "f1" in result and "A" not in result
    assert result["f1"] == 2


def test_all_same_gives_zero() -> None:
    problems = [_p("A", "f2", "MEDIUM")] * 5
    result = fid_severity_rank_below_mean(problems)
    assert result["f2"] == 0


def test_single_problem_gives_zero() -> None:
    problems = [_p("A", "f3", "CRITICAL")]
    result = fid_severity_rank_below_mean(problems)
    assert result["f3"] == 0


def test_all_low_except_one_high() -> None:
    # [INFO(0)*3, CRITICAL(4)] mean=0.8 -> INFO(0)<0.8 count=3
    problems = [_p("B", "f4", "INFO")] * 3 + [_p("B", "f4", "CRITICAL")]
    result = fid_severity_rank_below_mean(problems)
    assert result["f4"] == 3


def test_class_does_not_affect_fid_grouping() -> None:
    # different classes, same fid
    problems = [_p("X", "f5", "INFO"), _p("Y", "f5", "HIGH")]
    result = fid_severity_rank_below_mean(problems)
    # mean = (0+3)/2 = 1.5 -> INFO(0)<1.5 count=1
    assert result["f5"] == 1


def test_multiple_fids_independent() -> None:
    # f6: [HIGH,HIGH] -> 0; f7: [INFO,HIGH] -> mean=1.5, INFO<1.5 -> 1
    problems = ([_p("A", "f6", "HIGH"), _p("A", "f6", "HIGH")] +
                [_p("B", "f7", "INFO"), _p("B", "f7", "HIGH")])
    result = fid_severity_rank_below_mean(problems)
    assert result["f6"] == 0
    assert result["f7"] == 1


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_below_mean([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("A", "f8", "LOW"), _p("A", "f8", "HIGH")]
    result = fid_severity_rank_below_mean(problems)
    assert isinstance(result["f8"], int)


def test_strict_less_than_not_lte() -> None:
    # [LOW(1)*2, HIGH(3)] mean=5/3~1.667 -> LOW(1)<1.667 count=2 (strict <)
    problems = [_p("A", "f9", "LOW"), _p("A", "f9", "LOW"), _p("A", "f9", "HIGH")]
    result = fid_severity_rank_below_mean(problems)
    assert result["f9"] == 2


def test_symmetric_info_critical() -> None:
    # [INFO(0), CRITICAL(4)] mean=2.0 -> INFO below, CRITICAL above -> count=1
    problems = [_p("A", "f10", "INFO"), _p("A", "f10", "CRITICAL")]
    result = fid_severity_rank_below_mean(problems)
    assert result["f10"] == 1
