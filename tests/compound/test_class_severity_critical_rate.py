"""Item 649: class_severity_critical_rate() -- CRITICAL/total fraction per class.

Returns {class: count(CRITICAL) / total_class_problems}.
float in [0, 1].  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_critical_rate


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_rate_is_critical_over_total_not_ratio_primary_discriminator() -> None:
    """PRIMARY DISC.: rate = CRITICAL/total (NOT HIGH/LOW ratio).

    Class A: 2 CRITICAL + 3 HIGH -> rate=2/5=0.4.
    HIGH/LOW ratio would omit class A (no LOW) -- wrong.
    Kills impl using HIGH/LOW ratio or wrong numerator.
    """
    problems = [_p("A", "CRITICAL")] * 2 + [_p("A", "HIGH")] * 3
    result = class_severity_critical_rate(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key (no LOW should not cause omission); got {list(result)}"
    assert abs(result["A"] - 0.4) < 1e-9, (
        f"2 CRIT + 3 HIGH -> CRIT/total=0.4; got {result['A']} "
        f"(ratio impl would omit this class)"
    )
    assert isinstance(result["A"], float), "Must be float"


def test_no_critical_rate_zero() -> None:
    """No CRITICAL problems -> rate=0.0 (class is included, not omitted)."""
    problems = [_p("A", "HIGH")] * 5 + [_p("A", "LOW")] * 3
    result = class_severity_critical_rate(problems)
    assert "A" in result, f"Class with no CRITICAL must STILL be present; got {list(result)}"
    assert abs(result["A"]) < 1e-9, f"No CRITICAL -> rate=0.0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_critical_rate([]) == {}


def test_all_critical_rate_one() -> None:
    """All CRITICAL -> rate=1.0."""
    problems = [_p("A", "CRITICAL")] * 6
    result = class_severity_critical_rate(problems)
    assert "A" in result, f"Class A must be present"
    assert abs(result["A"] - 1.0) < 1e-9, f"All CRITICAL -> rate=1.0; got {result['A']}"


def test_multiple_classes_independent_rates() -> None:
    """Multiple classes each get independent critical rates.

    Class A: 1 CRIT + 4 HIGH -> rate=0.2.
    Class B: 3 CRIT + 3 LOW -> rate=0.5.
    """
    problems = (
        [_p("A", "CRITICAL")] + [_p("A", "HIGH")] * 4
        + [_p("B", "CRITICAL")] * 3 + [_p("B", "LOW")] * 3
    )
    result = class_severity_critical_rate(problems)
    assert abs(result["A"] - 0.2) < 1e-9, f"A: 1/5 -> 0.2; got {result.get('A')}"
    assert abs(result["B"] - 0.5) < 1e-9, f"B: 3/6 -> 0.5; got {result.get('B')}"
