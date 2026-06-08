"""Item 812: class_severity_rank_low_only_count() -- count rank==1 (LOW only) per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_low_only_count

def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)

def test_low_only_count_not_info_plus_low_primary_discriminator() -> None:
    problems = [_p("A", "LOW")] * 3 + [_p("A", "INFO")] * 2 + [_p("A", "MEDIUM")] * 1
    result = class_severity_rank_low_only_count(problems)
    got = result["A"]
    assert got == 3, f"low_only_count=3; got {got}"
    assert isinstance(got, int)
    assert got != 5

def test_info_only_gives_zero_not_excluded() -> None:
    problems = [_p("B", "INFO")] * 4 + [_p("B", "MEDIUM")] * 2
    result = class_severity_rank_low_only_count(problems)
    assert "B" in result and result["B"] == 0

def test_multi_class_independent() -> None:
    problems = [_p("X", "LOW")] * 5 + [_p("X", "INFO")] * 1 + [_p("Y", "INFO")] * 3
    result = class_severity_rank_low_only_count(problems)
    assert result.get("X") == 5 and result.get("Y") == 0

def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_low_only_count([]) == {}

def test_return_type_is_int() -> None:
    problems = [_p("D", "LOW"), _p("D", "INFO")]
    result = class_severity_rank_low_only_count(problems)
    assert isinstance(result["D"], int)
