"""Item 658: class_sev_low_rate() -- LOW/total fraction per class.

For each class: count(LOW) / total_class_problems.
float in [0, 1].  0.0 = no LOW.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_sev_low_rate


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_low_not_high_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: rate = LOW/total (NOT HIGH/total, NOT LOW/HIGH ratio).

    Class A: 2 HIGH + 3 LOW -> low_rate=0.6 (not 0.4 HIGH-rate wrong).
    Kills high-rate impl and ratio impl.
    """
    problems = [_p("A", "HIGH")] * 2 + [_p("A", "LOW")] * 3
    result = class_sev_low_rate(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert abs(result["A"] - 0.6) < 1e-9, (
        f"2 HIGH+3 LOW -> LOW/total=0.6; got {result['A']} (0.4=high-rate wrong)"
    )
    assert isinstance(result["A"], float), "Must be float"


def test_no_low_rate_zero() -> None:
    """No LOW problems -> rate=0.0 (class present with rate 0)."""
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "CRITICAL")]
    result = class_sev_low_rate(problems)
    assert "A" in result, f"Class must be present; got {result}"
    assert abs(result["A"]) < 1e-9, f"No LOW -> rate=0.0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_sev_low_rate([]) == {}


def test_all_low_rate_one() -> None:
    """All problems LOW -> rate=1.0."""
    problems = [_p("A", "LOW")] * 4
    result = class_sev_low_rate(problems)
    assert abs(result["A"] - 1.0) < 1e-9, f"All LOW -> 1.0; got {result.get('A')}"


def test_multiple_classes_independent_low_rates() -> None:
    """Multiple classes get independent LOW rates.

    Class X: 1 LOW + 4 HIGH -> low_rate=0.2.
    Class Y: 3 LOW + 0 HIGH -> low_rate=1.0.
    """
    problems = [_p("X", "LOW")] + [_p("X", "HIGH")] * 4 + [_p("Y", "LOW")] * 3
    result = class_sev_low_rate(problems)
    assert abs(result["X"] - 0.2) < 1e-9, f"X: 1/5 LOW -> 0.2; got {result.get('X')}"
    assert abs(result["Y"] - 1.0) < 1e-9, f"Y: 3/3 LOW -> 1.0; got {result.get('Y')}"
