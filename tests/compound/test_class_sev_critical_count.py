"""Item 660: class_sev_critical_count() -- raw count of CRITICAL problems per class.

For each class: count(CRITICAL).
int >= 0.  Classes with 0 CRITICAL included.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_sev_critical_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_raw_count_not_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: returns RAW COUNT not rate/fraction.

    Class A: 2 CRITICAL + 3 HIGH -> count=2 (not rate=0.4 wrong, not HIGH-count=3).
    Kills rate impl and wrong-severity impl.
    """
    problems = [_p("A", "CRITICAL")] * 2 + [_p("A", "HIGH")] * 3
    result = class_sev_critical_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert result["A"] == 2, (
        f"2 CRIT+3 HIGH -> count=2; got {result['A']} (rate=0.4 wrong, HIGH-count=3 wrong)"
    )
    assert isinstance(result["A"], int), "Must be int"


def test_zero_critical_class_included() -> None:
    """Class with 0 CRITICAL -> count=0 (class still present in result)."""
    problems = [_p("A", "HIGH")] * 4
    result = class_sev_critical_count(problems)
    assert "A" in result, f"Class must be present even with 0 CRITICAL; got {result}"
    assert result["A"] == 0, f"0 CRITICAL -> count=0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_sev_critical_count([]) == {}


def test_all_critical_count_equals_total() -> None:
    """All problems CRITICAL -> count = len(problems)."""
    problems = [_p("A", "CRITICAL")] * 6
    result = class_sev_critical_count(problems)
    assert result["A"] == 6, f"All CRIT -> count=6; got {result.get('A')}"


def test_multiple_classes_independent_counts() -> None:
    """Multiple classes each get independent CRITICAL counts.

    Class X: 3 CRITICAL + 2 LOW -> count=3.
    Class Y: 0 CRITICAL + 5 HIGH -> count=0.
    """
    problems = [_p("X", "CRITICAL")] * 3 + [_p("X", "LOW")] * 2 + [_p("Y", "HIGH")] * 5
    result = class_sev_critical_count(problems)
    assert result["X"] == 3, f"X: 3 CRIT -> count=3; got {result.get('X')}"
    assert result["Y"] == 0, f"Y: 0 CRIT -> count=0; got {result.get('Y')}"
