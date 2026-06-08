"""Item 814: class_severity_rank_high_only_count() -- count rank==3 (HIGH only) per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_high_only_count

def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)

def test_high_only_count_not_high_plus_critical_primary_discriminator() -> None:
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "CRITICAL")] * 2
    result = class_severity_rank_high_only_count(problems)
    got = result["A"]
    assert got == 3 and isinstance(got, int) and got != 5

def test_critical_only_gives_zero_not_excluded() -> None:
    problems = [_p("B", "CRITICAL")] * 4 + [_p("B", "MEDIUM")] * 2
    result = class_severity_rank_high_only_count(problems)
    assert "B" in result and result["B"] == 0

def test_multi_class_independent() -> None:
    problems = [_p("X", "HIGH")] * 4 + [_p("X", "CRITICAL")] * 1 + [_p("Y", "CRITICAL")] * 3
    result = class_severity_rank_high_only_count(problems)
    assert result.get("X") == 4 and result.get("Y") == 0

def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_high_only_count([]) == {}

def test_return_type_is_int() -> None:
    problems = [_p("D", "HIGH"), _p("D", "CRITICAL")]
    result = class_severity_rank_high_only_count(problems)
    assert isinstance(result["D"], int)
