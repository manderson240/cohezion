"""Item 852: class_severity_dominant_rank() -- rank with highest rank*count contribution per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_dominant_rank


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_weighted_not_frequency_primary_discriminator() -> None:
    # class A: 4 INFO(0) + 1 HIGH(3)
    # frequency: INFO wins (mode=0 wrong)
    # weighted: INFO 0*4=0, HIGH 3*1=3 -> HIGH dominates -> rank=3
    problems = [_p("A", "INFO")] * 4 + [_p("A", "HIGH")]
    result = class_severity_dominant_rank(problems)
    assert result["A"] == 3


def test_all_same_rank_returns_that_rank() -> None:
    problems = [_p("B", "MEDIUM")] * 5
    result = class_severity_dominant_rank(problems)
    assert result["B"] == 2


def test_tie_broken_by_highest_rank() -> None:
    # class C: 2 LOW(1)*2=2, 1 MEDIUM(2)*1=2 -> tie -> highest rank=2
    problems = [_p("C", "LOW")] * 2 + [_p("C", "MEDIUM")]
    result = class_severity_dominant_rank(problems)
    assert result["C"] == 2


def test_all_info_gives_rank_zero() -> None:
    # INFO rank=0; 0*N=0 for all N; only INFO present so dominant=0
    problems = [_p("D", "INFO")] * 3
    result = class_severity_dominant_rank(problems)
    assert result["D"] == 0


def test_critical_dominates_with_one_occurrence() -> None:
    # 5 LOW(1)*5=5 vs 1 CRITICAL(4)*1=4 -> LOW(5) wins
    problems = [_p("E", "LOW")] * 5 + [_p("E", "CRITICAL")]
    result = class_severity_dominant_rank(problems)
    assert result["E"] == 1


def test_critical_dominates_when_high_weight() -> None:
    # 2 CRITICAL(4)*2=8 vs 3 HIGH(3)*3=9 -> HIGH(9) wins
    problems = [_p("F", "CRITICAL")] * 2 + [_p("F", "HIGH")] * 3
    result = class_severity_dominant_rank(problems)
    assert result["F"] == 3


def test_multiple_classes_independent() -> None:
    # A: 2 INFO+1 HIGH -> HIGH(3) wins (0*2=0 < 3*1=3)
    # B: 3 CRITICAL -> CRITICAL(4)
    problems = [_p("A", "INFO"), _p("A", "INFO"), _p("A", "HIGH"),
                _p("B", "CRITICAL"), _p("B", "CRITICAL"), _p("B", "CRITICAL")]
    result = class_severity_dominant_rank(problems)
    assert result["A"] == 3
    assert result["B"] == 4


def test_empty_returns_empty_dict() -> None:
    assert class_severity_dominant_rank([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("G", "HIGH")]
    result = class_severity_dominant_rank(problems)
    assert isinstance(result["G"], int)


def test_single_problem_returns_its_rank() -> None:
    problems = [_p("H", "CRITICAL")]
    result = class_severity_dominant_rank(problems)
    assert result["H"] == 4
