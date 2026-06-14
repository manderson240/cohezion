"""Item 694: class_severity_rank_sum() -- sum of severity ranks per class.

Uses _SEVERITY_RANK: CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1, INFO=0.
class_severity_rank_sum(problems) -> dict[str, int].
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: sum of RANKS not sum of counts.
     class A: CRITICAL(4)+HIGH(3)+LOW(1) -> rank_sum=8.
     count-impl gives 3 wrong; simple-count wrong.
  2. Unknown severity contributes 0.
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_sum


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_sum_of_ranks_not_counts_primary_discriminator() -> None:
    """PRIMARY DISC.: sum RANKS (not problem count).

    class A: CRITICAL(4)+HIGH(3)+LOW(1) = 8.
    count-impl gives 3; distinct-count gives 3. Only rank-sum gives 8.
    """
    problems = [_p("A", "CRITICAL"), _p("A", "HIGH"), _p("A", "LOW")]
    result = class_severity_rank_sum(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class A must be present; got {list(result)}"
    assert result["A"] == 8, f"CRITICAL(4)+HIGH(3)+LOW(1)=8; got {result['A']} (count=3 wrong)"
    assert isinstance(result["A"], int), "Must be int"


def test_unknown_severity_contributes_zero() -> None:
    """Unknown severity strings contribute 0 to sum."""
    problems = [_p("B", "HIGH"), _p("B", "UNKNOWN_SEV")]
    result = class_severity_rank_sum(problems)
    assert result["B"] == 3, f"HIGH(3)+UNKNOWN(0)=3; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_sum([]) == {}


def test_multiple_classes_independent() -> None:
    """Classes computed independently."""
    problems = (
        [_p("C", "CRITICAL"), _p("C", "CRITICAL")]  # 4+4=8
        + [_p("D", "MEDIUM"), _p("D", "LOW")]  # 2+1=3
    )
    result = class_severity_rank_sum(problems)
    assert result["C"] == 8, f"C: 4+4=8; got {result.get('C')}"
    assert result["D"] == 3, f"D: 2+1=3; got {result.get('D')}"


def test_info_contributes_zero() -> None:
    """INFO has rank 0 so doesn't change sum."""
    problems = [_p("E", "HIGH"), _p("E", "INFO"), _p("E", "INFO")]
    result = class_severity_rank_sum(problems)
    assert result["E"] == 3, f"HIGH(3)+INFO(0)+INFO(0)=3; got {result.get('E')}"
