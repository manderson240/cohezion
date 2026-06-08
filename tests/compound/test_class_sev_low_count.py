"""Item 664: class_sev_low_count() -- raw count of LOW problems per class.

For each class: count(LOW).
int >= 0.  Classes with 0 LOW included.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: returns RAW COUNT of LOW (NOT HIGH count, NOT LOW/total rate).
     class A: 2 LOW + 4 HIGH -> count=2 (not HIGH-count=4, not rate=0.33).
     Kills HIGH-count impl and rate impl.
  2. Class with 0 LOW -> count=0 (zero-inclusive).
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Returns int (not float).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_sev_low_count,
)


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_low_count_not_high_count_not_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: returns RAW COUNT of LOW not HIGH count or rate.

    Class A: 2 LOW + 4 HIGH -> count=2 (not HIGH-count=4, not rate=0.33).
    Kills HIGH-count impl and rate impl.
    """
    problems = [_p("A", "LOW")] * 2 + [_p("A", "HIGH")] * 4
    result = class_sev_low_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert result["A"] == 2, (
        f"2 LOW+4 HIGH -> count=2; got {result['A']} "
        f"(HIGH-count=4 wrong, rate=0.33 wrong)"
    )
    assert isinstance(result["A"], int), "Must be int"


def test_zero_low_class_included() -> None:
    """Class with 0 LOW -> count=0 (class still present in result)."""
    problems = [_p("A", "HIGH")] * 3
    result = class_sev_low_count(problems)
    assert "A" in result, f"Class must be present even with 0 LOW; got {result}"
    assert result["A"] == 0, f"0 LOW -> count=0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_sev_low_count([]) == {}


def test_all_low_count_equals_total() -> None:
    """All problems LOW -> count = len(problems)."""
    problems = [_p("A", "LOW")] * 5
    result = class_sev_low_count(problems)
    assert result["A"] == 5, f"All LOW -> count=5; got {result.get('A')}"


def test_multiple_classes_independent_low_counts() -> None:
    """Multiple classes get independent LOW counts.

    Class X: 3 LOW + 2 HIGH -> count=3.
    Class Y: 0 LOW + 4 CRITICAL -> count=0.
    """
    problems = [_p("X", "LOW")] * 3 + [_p("X", "HIGH")] * 2 + [_p("Y", "CRITICAL")] * 4
    result = class_sev_low_count(problems)
    assert result["X"] == 3, f"X: 3 LOW -> count=3; got {result.get('X')}"
    assert result["Y"] == 0, f"Y: 0 LOW -> count=0; got {result.get('Y')}"
