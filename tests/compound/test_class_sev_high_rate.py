"""Item 656: class_sev_high_rate() -- HIGH/total fraction per class.

For each class: count(HIGH) / total_class_problems.
float in [0, 1].  0.0 = no HIGH.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_sev_high_rate


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_rate_not_ratio_primary_discriminator() -> None:
    """PRIMARY DISC.: rate = HIGH/total (NOT HIGH/LOW ratio, NOT CRITICAL/total).

    Class A: 2 HIGH + 3 LOW -> high_rate=0.4 (not HIGH/LOW=0.67).
    Kills ratio impl; kills critical-rate impl.
    """
    problems = [_p("A", "HIGH")] * 2 + [_p("A", "LOW")] * 3
    result = class_sev_high_rate(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert abs(result["A"] - 0.4) < 1e-9, (
        f"2 HIGH+3 LOW -> HIGH/total=0.4; got {result['A']} (HIGH/LOW=0.67 wrong)"
    )
    assert isinstance(result["A"], float), "Must be float"


def test_no_high_rate_zero() -> None:
    """No HIGH problems -> rate=0.0 (class present with rate 0)."""
    problems = [_p("A", "LOW")] * 4 + [_p("A", "CRITICAL")]
    result = class_sev_high_rate(problems)
    assert "A" in result, f"Class must be present; got {result}"
    assert abs(result["A"]) < 1e-9, f"No HIGH -> rate=0.0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_sev_high_rate([]) == {}


def test_all_high_rate_one() -> None:
    """All problems HIGH -> rate=1.0."""
    problems = [_p("A", "HIGH")] * 5
    result = class_sev_high_rate(problems)
    assert abs(result["A"] - 1.0) < 1e-9, f"All HIGH -> 1.0; got {result.get('A')}"


def test_multiple_classes_independent_rates() -> None:
    """Multiple classes get independent HIGH rates.

    Class X: 4 HIGH + 1 LOW -> high_rate=0.8.
    Class Y: 0 HIGH + 3 CRITICAL -> high_rate=0.0.
    """
    problems = [_p("X", "HIGH")] * 4 + [_p("X", "LOW")] + [_p("Y", "CRITICAL")] * 3
    result = class_sev_high_rate(problems)
    assert abs(result["X"] - 0.8) < 1e-9, f"X: 4/5 -> 0.8; got {result.get('X')}"
    assert abs(result["Y"]) < 1e-9, f"Y: 0 HIGH -> 0.0; got {result.get('Y')}"
