"""Item 702: class_severity_rank_range() -- severity rank range per class (max_rank - min_rank).

class_severity_rank_range(problems) -> dict[str, int].
Range = max(_SEVERITY_RANK[sev]) - min(_SEVERITY_RANK[sev]) for class.
Single or identical severities -> 0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: range = max - min (NOT spread count, NOT count);
     class A: CRITICAL(4)+LOW(1) -> range=4-1=3;
     spread-impl gives 2 (distinct count) wrong; count-impl gives 2 wrong.
  2. Single severity -> range = 0 (max == min).
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Same severity repeated -> range = 0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_range


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_range_max_minus_min_primary_discriminator() -> None:
    """PRIMARY DISC.: range = max_rank - min_rank.

    class A: CRITICAL(4)+LOW(1) -> range=4-1=3.
    spread-impl gives 2 (2 distinct severities) wrong; count-impl gives 2 wrong.
    """
    problems = [_p("A", "CRITICAL"), _p("A", "LOW")]
    result = class_severity_rank_range(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be outer key; got {list(result)}"
    assert result["A"] == 3, (
        f"CRITICAL(4)-LOW(1)=3; got {result['A']} (spread=2 wrong, count=2 wrong)"
    )
    assert isinstance(result["A"], int), f"Must be int; got {type(result['A'])}"


def test_single_severity_range_zero() -> None:
    """Single severity -> range = 0 (max == min)."""
    problems = [_p("B", "HIGH"), _p("B", "HIGH")]
    result = class_severity_rank_range(problems)
    assert result["B"] == 0, f"All HIGH -> range=0; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_range([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class computes its own range."""
    problems = [_p("X", "CRITICAL"), _p("X", "INFO")]  # 4-0=4
    problems += [_p("Y", "HIGH"), _p("Y", "MEDIUM")]  # 3-2=1
    result = class_severity_rank_range(problems)
    assert result["X"] == 4, f"X: CRIT-INFO=4; got {result.get('X')}"
    assert result["Y"] == 1, f"Y: HIGH-MED=1; got {result.get('Y')}"


def test_identical_severities_range_zero() -> None:
    """Multiple of same severity -> range = 0."""
    problems = [_p("Z", "MEDIUM")] * 5
    result = class_severity_rank_range(problems)
    assert result["Z"] == 0, f"5 MEDIUM -> range=0; got {result.get('Z')}"
