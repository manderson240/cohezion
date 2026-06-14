"""Item 662: class_sev_high_count() -- raw count of HIGH problems per class.

For each class: count(HIGH).
int >= 0.  Classes with 0 HIGH included.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_sev_high_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_high_count_not_rate_not_critical_primary_discriminator() -> None:
    """PRIMARY DISC.: raw count of HIGH (NOT rate, NOT CRITICAL count).

    Class A: 3 HIGH + 2 CRITICAL -> count=3 (not rate=0.6, not crit-count=2).
    Kills rate impl and wrong-severity impl.
    """
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "CRITICAL")] * 2
    result = class_sev_high_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert result["A"] == 3, (
        f"3 HIGH+2 CRIT -> count=3; got {result['A']} (rate=0.6 wrong, crit=2 wrong)"
    )
    assert isinstance(result["A"], int), "Must be int"


def test_zero_high_class_included() -> None:
    """Class with 0 HIGH -> count=0 (class still present)."""
    problems = [_p("A", "LOW")] * 4
    result = class_sev_high_count(problems)
    assert "A" in result
    assert result["A"] == 0, f"0 HIGH -> count=0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_sev_high_count([]) == {}


def test_all_high_count_equals_total() -> None:
    """All HIGH -> count = total."""
    problems = [_p("A", "HIGH")] * 5
    result = class_sev_high_count(problems)
    assert result["A"] == 5, f"5 HIGH -> count=5; got {result.get('A')}"


def test_multiple_classes_independent_high_counts() -> None:
    """Multiple classes get independent HIGH counts."""
    problems = [_p("X", "HIGH")] * 4 + [_p("X", "LOW")] + [_p("Y", "CRITICAL")] * 3
    result = class_sev_high_count(problems)
    assert result["X"] == 4, f"X: 4 HIGH -> count=4; got {result.get('X')}"
    assert result["Y"] == 0, f"Y: 0 HIGH -> count=0; got {result.get('Y')}"
