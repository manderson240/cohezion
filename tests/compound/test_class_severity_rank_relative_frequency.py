"""Item 862: class_severity_rank_relative_frequency() -- fraction per rank per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_relative_frequency


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_two_level_float_not_count_primary_discriminator() -> None:
    # class A: 2 HIGH(3)+2 LOW(1)+1 INFO(0) -> {3:0.4, 1:0.4, 0:0.2}
    # count-impl gives {3:2, 1:2, 0:1} wrong; flat-dict wrong
    problems = [_p("A", "HIGH"), _p("A", "HIGH"), _p("A", "LOW"), _p("A", "LOW"), _p("A", "INFO")]
    result = class_severity_rank_relative_frequency(problems)
    assert abs(result["A"][3] - 0.4) < 1e-9
    assert abs(result["A"][1] - 0.4) < 1e-9
    assert abs(result["A"][0] - 0.2) < 1e-9


def test_fractions_sum_to_one() -> None:
    problems = [_p("B", "INFO"), _p("B", "LOW"), _p("B", "MEDIUM"), _p("B", "HIGH"), _p("B", "CRITICAL")]
    result = class_severity_rank_relative_frequency(problems)
    assert abs(sum(result["B"].values()) - 1.0) < 1e-9


def test_single_rank_gives_fraction_one() -> None:
    problems = [_p("C", "HIGH")] * 5
    result = class_severity_rank_relative_frequency(problems)
    assert abs(result["C"][3] - 1.0) < 1e-9
    assert len(result["C"]) == 1


def test_two_ranks_equal_gives_half() -> None:
    problems = [_p("D", "HIGH"), _p("D", "LOW")]
    result = class_severity_rank_relative_frequency(problems)
    assert abs(result["D"][3] - 0.5) < 1e-9
    assert abs(result["D"][1] - 0.5) < 1e-9


def test_multiple_classes_independent() -> None:
    problems = [_p("X", "CRITICAL"), _p("X", "CRITICAL"),  # X: {4:1.0}
                _p("Y", "HIGH"), _p("Y", "LOW")]             # Y: {3:0.5, 1:0.5}
    result = class_severity_rank_relative_frequency(problems)
    assert abs(result["X"][4] - 1.0) < 1e-9
    assert abs(result["Y"][3] - 0.5) < 1e-9


def test_return_type_is_float() -> None:
    problems = [_p("E", "MEDIUM"), _p("E", "HIGH")]
    result = class_severity_rank_relative_frequency(problems)
    assert isinstance(result["E"][2], float)
    assert isinstance(result["E"][3], float)


def test_outer_key_is_class() -> None:
    problems = [_p("F", "HIGH")]
    result = class_severity_rank_relative_frequency(problems)
    assert "F" in result
    assert isinstance(list(result["F"].keys())[0], int)


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_relative_frequency([]) == {}


def test_absent_ranks_not_in_result() -> None:
    # Only HIGH present — INFO/LOW/MEDIUM/CRITICAL ranks should NOT appear
    problems = [_p("G", "HIGH")] * 3
    result = class_severity_rank_relative_frequency(problems)
    assert set(result["G"].keys()) == {3}


def test_four_equal_ranks() -> None:
    problems = [_p("H", s) for s in ["INFO", "LOW", "MEDIUM", "HIGH"]]
    result = class_severity_rank_relative_frequency(problems)
    for rank in [0, 1, 2, 3]:
        assert abs(result["H"][rank] - 0.25) < 1e-9
