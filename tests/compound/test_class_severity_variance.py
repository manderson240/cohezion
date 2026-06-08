"""Item 604: class_severity_variance() -- variance of severity counts per class.

``class_severity_variance(problems) -> dict[str, float]``:
Returns {class: population_variance_of_per_severity_counts}.
Variance of raw INTEGER counts, NOT probabilities.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: variance of RAW counts (not probability values).
     HIGH=4, LOW=1: counts=[4,1], mean=2.5, var=2.25 (NOT Gini-style 0.32).
  2. Uniform distribution -> 0.0 (all counts equal -> no spread).
  3. Single-severity -> 0.0 (variance of a single value is zero).
  4. Empty -> {}.
  5. Three-severity: HIGH=3, MEDIUM=2, LOW=1 -> counts=[3,2,1], mean=2, var=2/3.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_variance


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_variance_of_raw_counts_not_probabilities_primary_discriminator() -> None:
    """PRIMARY DISC.: variance of raw INTEGER counts, NOT probability fractions.

    HIGH=4, LOW=1: counts=[4,1], mean=2.5.
    var = ((4-2.5)^2 + (1-2.5)^2) / 2 = (2.25 + 2.25) / 2 = 2.25.
    Gini/probability variance would give (0.8-0.5)^2+(0.2-0.5)^2)/2 = 0.09.
    Kills impl computing variance of probabilities.
    """
    problems = [_p("A", "HIGH")] * 4 + [_p("A", "LOW")]
    result = class_severity_variance(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {list(result)}"
    assert abs(result["A"] - 2.25) < 1e-9, (
        f"counts=[4,1], var=2.25; got {result['A']} "
        f"(0.09 = probability variance, not count variance)"
    )


def test_uniform_distribution_zero_variance() -> None:
    """Uniform distribution -> variance=0.0 (all counts equal).

    HIGH=3, LOW=3: counts=[3,3], mean=3, var=0.
    Kills impl returning non-zero for uniform data.
    """
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")] * 3
    result = class_severity_variance(problems)
    assert abs(result["A"]) < 1e-9, (
        f"Uniform [3,3] -> var=0.0; got {result['A']}"
    )


def test_single_severity_zero_variance() -> None:
    """Single severity -> variance=0.0 (one count, no spread).

    Kills impl that errors or returns non-zero for a single bucket.
    """
    problems = [_p("A", "CRITICAL")] * 7
    result = class_severity_variance(problems)
    assert abs(result["A"]) < 1e-9, f"Single-severity -> var=0.0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_variance([]) == {}


def test_three_severity_variance() -> None:
    """HIGH=3, MEDIUM=2, LOW=1: counts=[3,2,1], mean=2, var=2/3.

    var = ((3-2)^2 + (2-2)^2 + (1-2)^2) / 3 = (1+0+1)/3 = 2/3.
    Kills impl with wrong formula or wrong normalization.
    """
    problems = (
        [_p("A", "HIGH")] * 3 + [_p("A", "MEDIUM")] * 2 + [_p("A", "LOW")]
    )
    result = class_severity_variance(problems)
    expected = 2.0 / 3.0
    assert abs(result["A"] - expected) < 1e-9, (
        f"counts=[3,2,1] -> var=2/3={expected:.6f}; got {result['A']}"
    )
