"""Item 784: class_severity_rank_count_at_rank() -- count at exact rank per class.

class_severity_rank_count_at_rank(problems, rank) -> dict[str, int].
Returns {class: count} for every class in problems; count=0 if none at that rank.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: count at exact rank != at-or-above; class A:
     [CRITICAL(4)*3, HIGH(3)*2]; count_at_rank(3)=2; at-or-above(3)-impl=5 wrong.
  2. Zero for class with none at rank (class not excluded).
  3. All-same: rank matches -> n; rank != -> 0.
  4. Empty -> {}.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_count_at_rank


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_exact_rank_not_at_or_above_primary_discriminator() -> None:
    """PRIMARY DISC.: count_at_rank(3)=2; at-or-above(3)-impl=5 wrong.

    class A: [CRITICAL(4)*3, HIGH(3)*2].
    count_at_rank(3) = HIGH count = 2.
    at-or-above(3)-impl would give 3+2=5 (wrong).
    """
    problems = [_p("A", "CRITICAL")] * 3 + [_p("A", "HIGH")] * 2
    result = class_severity_rank_count_at_rank(problems, 3)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert got == 2, f"count_at_rank(3) for [CRIT*3,HIGH*2] = 2; got {got}"
    assert got != 5, "Must be exact count not at-or-above (5 is wrong)"


def test_zero_for_class_with_no_matching_rank() -> None:
    """Class present but no problems at target rank -> count=0 (not excluded)."""
    problems = [_p("B", "CRITICAL")] * 2 + [_p("B", "HIGH")] * 2
    result = class_severity_rank_count_at_rank(problems, 2)  # rank=2 = MEDIUM, none
    assert "B" in result, "Class B must still appear in result with count=0"
    assert result["B"] == 0, f"No MEDIUM in [CRIT*2,HIGH*2] -> 0; got {result['B']}"


def test_all_same_rank_matches_and_misses() -> None:
    """All same rank: matching rank -> n; non-matching rank -> 0."""
    problems = [_p("C", "HIGH")] * 4
    result_match = class_severity_rank_count_at_rank(problems, 3)  # HIGH=3
    result_miss = class_severity_rank_count_at_rank(problems, 4)  # CRITICAL=4, none
    assert result_match.get("C") == 4, (
        f"All HIGH -> count_at_rank(3)=4; got {result_match.get('C')}"
    )
    assert result_miss.get("C") == 0, f"All HIGH -> count_at_rank(4)=0; got {result_miss.get('C')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_count_at_rank([], 3) == {}


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("D", "HIGH"), _p("D", "INFO")]
    result = class_severity_rank_count_at_rank(problems, 3)
    assert isinstance(result["D"], int), f"Must be int; got {type(result['D'])}"
