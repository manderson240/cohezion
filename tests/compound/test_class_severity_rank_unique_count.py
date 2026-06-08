"""Item 755: class_severity_rank_unique_count() -- distinct severity rank count per class.

class_severity_rank_unique_count(problems) -> dict[str, int].
Count of distinct _SEVERITY_RANK values present per class.
All-same -> 1.  n=1 -> 1.  Empty -> {}.  Returns int.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: unique count not total count; class A: INFO(0)*3+HIGH(3)*2
     -> unique=2 (two distinct ranks); total-count-impl gives 5 wrong; entropy-impl wrong.
  2. All-same -> 1 (only one distinct rank).
  3. All five ranks present -> 5.
  4. Empty -> {}.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_unique_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_unique_not_total_primary_discriminator() -> None:
    """PRIMARY DISC.: unique=2 not total=5; class A: INFO*3+HIGH*2 -> 2 distinct ranks.

    total-count-impl gives 5 wrong; all-one-impl gives 1 wrong.
    """
    problems = [_p("A", "INFO"), _p("A", "INFO"), _p("A", "INFO"),
                _p("A", "HIGH"), _p("A", "HIGH")]
    result = class_severity_rank_unique_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert got == 2, f"INFO*3+HIGH*2 -> 2 distinct ranks; got {got}"
    assert got != 5, "Must be unique count not total count"
    assert got != 1, "Must be unique count not all-one"


def test_all_same_gives_one() -> None:
    """All same severity -> unique_count = 1."""
    problems = [_p("B", "CRITICAL")] * 5
    result = class_severity_rank_unique_count(problems)
    got = result.get("B")
    assert got == 1, f"All CRITICAL -> 1; got {got}"


def test_all_five_ranks_gives_five() -> None:
    """All five severity ranks present -> unique_count = 5."""
    problems = [
        _p("C", "INFO"), _p("C", "LOW"), _p("C", "MEDIUM"),
        _p("C", "HIGH"), _p("C", "CRITICAL"),
    ]
    result = class_severity_rank_unique_count(problems)
    got = result.get("C")
    assert got == 5, f"All 5 ranks -> 5; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_unique_count([]) == {}


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("D", "INFO"), _p("D", "INFO"), _p("D", "CRITICAL")]
    result = class_severity_rank_unique_count(problems)
    assert isinstance(result["D"], int), f"Must be int; got {type(result['D'])}"
