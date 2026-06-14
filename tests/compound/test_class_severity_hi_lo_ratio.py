"""Item 647: class_severity_hi_lo_ratio() -- HIGH/LOW severity ratio per class.

ratio = count(HIGH) / count(LOW).
float > 0.0.  Classes with no LOW are omitted (undefined ratio).
Classes with no HIGH are also omitted (ratio would be 0.0).
Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_hi_lo_ratio


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_ratio_not_concentration_primary_discriminator() -> None:
    """PRIMARY DISC.: ratio = HIGH/LOW (NOT HIGH/total, NOT max_sev_count/total).

    class A: 6 HIGH + 2 LOW -> ratio=3.0.
    concentration = 6/8 = 0.75 wrong; total=8 wrong.
    Kills impl using concentration or total-denominator.
    """
    problems = [_p("A", "HIGH")] * 6 + [_p("A", "LOW")] * 2
    result = class_severity_hi_lo_ratio(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert abs(result["A"] - 3.0) < 1e-9, (
        f"6 HIGH, 2 LOW -> ratio=3.0; got {result['A']} "
        f"(concentration=0.75 wrong, total-denom wrong)"
    )
    assert isinstance(result["A"], float), "Must be float"


def test_no_low_class_omitted() -> None:
    """Class with no LOW problems -> omitted (undefined denominator)."""
    problems = [_p("B", "HIGH")] * 4
    result = class_severity_hi_lo_ratio(problems)
    assert "B" not in result, f"Class with no LOW must be omitted; got {result}"


def test_equal_high_low_ratio_one() -> None:
    """Equal HIGH and LOW -> ratio=1.0."""
    problems = [_p("C", "HIGH")] * 3 + [_p("C", "LOW")] * 3
    result = class_severity_hi_lo_ratio(problems)
    assert "C" in result
    assert abs(result["C"] - 1.0) < 1e-9, f"3 HIGH, 3 LOW -> ratio=1.0; got {result['C']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_hi_lo_ratio([]) == {}


def test_multiple_classes_independent() -> None:
    """Multiple classes: each gets independent ratio; no-LOW class omitted.

    Class X: 4 HIGH, 2 LOW -> ratio=2.0.
    Class Y: 0 HIGH, 3 LOW -> omitted (ratio=0.0, below threshold).
    """
    problems = [_p("X", "HIGH")] * 4 + [_p("X", "LOW")] * 2 + [_p("Y", "LOW")] * 3
    result = class_severity_hi_lo_ratio(problems)
    assert abs(result["X"] - 2.0) < 1e-9, f"X: 4 HIGH, 2 LOW -> ratio=2.0; got {result.get('X')}"
    assert "Y" not in result, f"Y: no HIGH -> omitted; got {result}"
