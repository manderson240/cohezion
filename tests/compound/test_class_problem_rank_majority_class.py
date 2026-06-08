"""Item 746: class_problem_rank_majority_class() -- majority severity rank per class.

class_problem_rank_majority_class(problems) -> dict[str, int].
Returns the rank (int) with highest count per class; ties broken by min rank.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: returns rank INT not label str; class A: INFO(0)*3+HIGH(3)*2
     -> majority_rank=0 (count 3>2); label-impl gives "INFO" wrong; count-impl gives 3 wrong.
  2. Tie broken by min rank.
  3. Single problem -> that rank.
  4. Empty -> {}.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_problem_rank_majority_class


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_majority_rank_int_primary_discriminator() -> None:
    """PRIMARY DISC.: returns rank INT; INFO(0)*3 > HIGH(3)*2 -> majority_rank=0.

    class A: INFO(0)*3+HIGH(3)*2 -> rank 0 has count 3 > rank 3 has count 2 -> 0.
    label-impl gives 'INFO' wrong; count-impl gives 3 wrong.
    """
    problems = [_p("A", "INFO"), _p("A", "INFO"), _p("A", "INFO"),
                _p("A", "HIGH"), _p("A", "HIGH")]
    result = class_problem_rank_majority_class(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    got = result["A"]
    assert got == 0, f"INFO(0)*3 > HIGH(3)*2 -> rank=0; got {got!r} (label 'INFO' wrong, count 3 wrong)"
    assert isinstance(got, int), f"Must be int not str; got {type(got)}"


def test_tie_broken_by_min_rank() -> None:
    """Tie: min rank wins; HIGH(3)*2+MEDIUM(2)*2 -> rank=2 (min of tied 2,3)."""
    problems = [_p("B", "HIGH"), _p("B", "HIGH"), _p("B", "MEDIUM"), _p("B", "MEDIUM")]
    result = class_problem_rank_majority_class(problems)
    got = result.get("B")
    assert got == 2, f"HIGH(3)*2 tie MEDIUM(2)*2 -> rank=2 (min); got {got}"


def test_single_problem() -> None:
    """Single problem -> that problem's rank."""
    result = class_problem_rank_majority_class([_p("C", "CRITICAL")])
    got = result.get("C")
    assert got == 4, f"CRITICAL -> rank=4; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_problem_rank_majority_class([]) == {}


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("D", "HIGH"), _p("D", "HIGH")]
    result = class_problem_rank_majority_class(problems)
    assert isinstance(result["D"], int), f"Must be int; got {type(result['D'])}"
    assert result["D"] == 3, f"HIGH*2 -> rank=3; got {result['D']}"
