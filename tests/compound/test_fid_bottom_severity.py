"""Item 867: fid_bottom_severity() -- least severe problem severity label per fid."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, fid_bottom_severity


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_outer_key_fid_not_class_primary_discriminator() -> None:
    # fid f1: [INFO(0), HIGH(3)] -> "INFO"; outer key must be FID not class
    problems = [_p("A", "f1", "INFO"), _p("A", "f1", "HIGH")]
    result = fid_bottom_severity(problems)
    assert "f1" in result
    assert result["f1"] == "INFO"


def test_min_label_not_max() -> None:
    # fid f2: [LOW, MEDIUM, CRITICAL] -> "LOW"
    problems = [_p("B", "f2", "LOW"), _p("B", "f2", "MEDIUM"), _p("B", "f2", "CRITICAL")]
    result = fid_bottom_severity(problems)
    assert result["f2"] == "LOW"


def test_single_problem_returns_its_severity() -> None:
    problems = [_p("C", "f3", "HIGH")]
    result = fid_bottom_severity(problems)
    assert result["f3"] == "HIGH"


def test_all_same_rank_returns_that_label() -> None:
    problems = [_p("D", "f4", "MEDIUM")] * 4
    result = fid_bottom_severity(problems)
    assert result["f4"] == "MEDIUM"


def test_many_high_does_not_override_single_info() -> None:
    problems = [_p("E", "f5", "HIGH")] * 5 + [_p("E", "f5", "INFO")]
    result = fid_bottom_severity(problems)
    assert result["f5"] == "INFO"


def test_class_does_not_affect_fid_grouping() -> None:
    # same fid, different classes -> keyed by fid
    problems = [_p("X", "f6", "HIGH"), _p("Y", "f6", "LOW")]
    result = fid_bottom_severity(problems)
    assert result["f6"] == "LOW"


def test_multiple_fids_independent() -> None:
    # f7: [CRITICAL, LOW] -> "LOW"; f8: [HIGH, HIGH] -> "HIGH"
    problems = ([_p("A", "f7", "CRITICAL"), _p("A", "f7", "LOW")] +
                [_p("B", "f8", "HIGH"), _p("B", "f8", "HIGH")])
    result = fid_bottom_severity(problems)
    assert result["f7"] == "LOW"
    assert result["f8"] == "HIGH"


def test_empty_returns_empty_dict() -> None:
    assert fid_bottom_severity([]) == {}


def test_return_type_is_str() -> None:
    problems = [_p("G", "f9", "MEDIUM")]
    result = fid_bottom_severity(problems)
    assert isinstance(result["f9"], str)


def test_info_lowest_rank_wins() -> None:
    # All five ranks -> "INFO" because INFO has rank 0
    problems = [_p("H", "f10", s) for s in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]
    result = fid_bottom_severity(problems)
    assert result["f10"] == "INFO"
