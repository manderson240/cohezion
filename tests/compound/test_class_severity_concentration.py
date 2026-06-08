"""Item 622: class_severity_concentration() -- dominance of the most frequent severity per class.

Returns {class: max_severity_count / total_class_problems}.
float in (0.0, 1.0].  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_concentration


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_max_over_total_not_gini_not_count_primary_discriminator() -> None:
    """PRIMARY DISC.: returns max_sev_count / total_count (NOT Gini, NOT int count, NOT label).

    Class A: HIGH=6, LOW=4 -> total=10, max=6 -> concentration=0.6.
    Gini would give 0.48; max_count int would give 6; top_severity label would give 'HIGH'.
    Kills impl that returns Gini, absolute count, or severity label.
    """
    problems = [_p("A", "HIGH")] * 6 + [_p("A", "LOW")] * 4
    result = class_severity_concentration(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert abs(result["A"] - 0.6) < 1e-9, (
        f"HIGH=6, LOW=4 -> max/total = 6/10 = 0.6; got {result['A']} "
        f"(Gini=0.48 wrong, count=6 wrong, label='HIGH' wrong)"
    )
    assert isinstance(result["A"], float), "Must be float; got " + type(result["A"]).__name__


def test_single_severity_returns_one() -> None:
    """Single severity bucket -> all problems in one bucket -> concentration=1.0."""
    problems = [_p("A", "CRITICAL")] * 7
    result = class_severity_concentration(problems)
    assert abs(result["A"] - 1.0) < 1e-9, (
        f"Single severity -> concentration=1.0; got {result['A']}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_concentration([]) == {}


def test_multiple_classes_independent_concentrations() -> None:
    """Multiple classes each get independent concentration.

    Class A: HIGH=3, LOW=1 -> max=3, total=4 -> concentration=0.75.
    Class B: HIGH=1, LOW=1, MED=1 -> max=1, total=3 -> concentration=1/3.
    """
    problems = (
        [_p("A", "HIGH")] * 3 + [_p("A", "LOW")]
        + [_p("B", "HIGH"), _p("B", "LOW"), _p("B", "MED")]
    )
    result = class_severity_concentration(problems)
    assert abs(result["A"] - 0.75) < 1e-9, (
        f"A: HIGH=3, LOW=1 -> 3/4=0.75; got {result['A']}"
    )
    assert abs(result["B"] - 1.0 / 3.0) < 1e-9, (
        f"B: 3 equal severities -> 1/3=0.333; got {result['B']}"
    )


def test_values_in_zero_to_one() -> None:
    """All concentration values in (0, 1]."""
    problems = (
        [_p("A", "HIGH")] * 5 + [_p("A", "LOW")] * 3 + [_p("A", "MED")] * 2
        + [_p("B", "CRITICAL")] * 4 + [_p("B", "LOW")]
    )
    result = class_severity_concentration(problems)
    for cls, concentration in result.items():
        assert 0.0 < concentration <= 1.0, (
            f"Concentration for {cls} out of (0,1]: {concentration}"
        )
