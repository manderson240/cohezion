"""Item 606: class_severity_range() -- range of severity counts per class.

Returns {class: max_count - min_count}.  int not float.  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_range


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_max_minus_min_not_variance_primary_discriminator() -> None:
    """PRIMARY DISC.: returns integer max-min, NOT float variance.

    HIGH=5, LOW=1 -> range=4 (int).
    Variance would be 4.0 (float).
    """
    problems = [_p("A", "HIGH")] * 5 + [_p("A", "LOW")]
    result = class_severity_range(problems)
    assert isinstance(result, dict), "Must return dict"
    assert result["A"] == 4, f"max=5, min=1 -> range=4; got {result['A']}"
    assert isinstance(result["A"], int), (
        "Range must be int; got " + type(result["A"]).__name__
    )


def test_single_severity_range_zero() -> None:
    """Single severity -> range=0 (only one bucket, max==min)."""
    problems = [_p("A", "CRITICAL")] * 7
    result = class_severity_range(problems)
    assert result["A"] == 0, f"Single-severity -> range=0; got {result['A']}"


def test_uniform_distribution_range_zero() -> None:
    """All severities equal counts -> range=0."""
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")] * 3
    result = class_severity_range(problems)
    assert result["A"] == 0, f"Uniform [3,3] -> range=0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_range([]) == {}


def test_three_severity_range() -> None:
    """HIGH=5, MEDIUM=2, LOW=1 -> range=5-1=4."""
    problems = (
        [_p("A", "HIGH")] * 5 + [_p("A", "MEDIUM")] * 2 + [_p("A", "LOW")]
    )
    result = class_severity_range(problems)
    assert result["A"] == 4, f"max=5, min=1 -> range=4; got {result['A']}"
