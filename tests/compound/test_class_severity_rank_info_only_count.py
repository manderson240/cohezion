"""Item 820: class_severity_rank_info_only_count() -- count rank==0 (INFO only) per class."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, class_severity_rank_info_only_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_info_only_count_not_low_plus_info_primary_discriminator() -> None:
    problems = [_p("A", "INFO")] * 3 + [_p("A", "LOW")] * 2
    result = class_severity_rank_info_only_count(problems)
    got = result["A"]
    # info_only=3; low_count (rank<=1)=5 wrong; info_fraction=3/5=0.6 wrong; must be int
    assert got == 3 and isinstance(got, int) and got != 5


def test_low_only_gives_zero_not_excluded() -> None:
    problems = [_p("B", "LOW")] * 4 + [_p("B", "MEDIUM")] * 2
    result = class_severity_rank_info_only_count(problems)
    assert "B" in result and result["B"] == 0


def test_multi_class_independent() -> None:
    problems = [_p("X", "INFO")] * 4 + [_p("X", "LOW")] * 1 + [_p("Y", "LOW")] * 3
    result = class_severity_rank_info_only_count(problems)
    assert result.get("X") == 4 and result.get("Y") == 0


def test_empty_returns_empty_dict() -> None:
    assert class_severity_rank_info_only_count([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("D", "INFO"), _p("D", "LOW")]
    result = class_severity_rank_info_only_count(problems)
    assert isinstance(result["D"], int)
