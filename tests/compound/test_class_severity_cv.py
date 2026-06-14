"""Item 625: class_severity_cv() -- coefficient of variation of severity counts per class.

CV = population_std_dev / mean of the per-severity INTEGER counts.
Measures relative spread; complementary to variance (item 604).
0.0 = all severities equal count (or single severity: std=0).
float >= 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: CV = std / mean of RAW counts (NOT probability-space CV, NOT variance).
     HIGH=4, LOW=1: counts=[4,1], mean=2.5, std=sqrt(2.25)=1.5, cv=1.5/2.5=0.6.
     variance alone = 2.25; kills impl returning variance instead of cv.
  2. Uniform distribution -> CV=0.0 (std=0, mean=k, cv=0).
     HIGH=3, LOW=3: counts=[3,3], std=0, cv=0.
  3. Single-severity -> CV=0.0 (std=0, mean=count, cv=0).
  4. Empty -> {}.
  5. Three-severity: HIGH=3, MED=2, LOW=1 -> std=sqrt(2/3), mean=2, cv=sqrt(2/3)/2.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import Problem, class_severity_cv


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_cv_is_std_over_mean_not_variance_primary_discriminator() -> None:
    """PRIMARY DISC.: CV = std / mean of RAW INTEGER counts (NOT variance).

    Class A: HIGH=4, LOW=1 -> counts=[4,1], mean=2.5.
    population_std = sqrt(((4-2.5)^2 + (1-2.5)^2) / 2) = sqrt(2.25) = 1.5.
    cv = 1.5 / 2.5 = 0.6.
    variance alone = 2.25 -- kills impl returning variance instead of cv.
    """
    problems = [_p("A", "HIGH")] * 4 + [_p("A", "LOW")]
    result = class_severity_cv(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {list(result)}"
    expected = 1.5 / 2.5  # 0.6
    assert abs(result["A"] - expected) < 1e-9, (
        f"HIGH=4,LOW=1 -> counts=[4,1], mean=2.5, std=1.5, cv=1.5/2.5=0.6; "
        f"got {result['A']} (2.25=variance, 0.6=correct cv)"
    )


def test_uniform_distribution_zero_cv() -> None:
    """Uniform distribution -> CV=0.0 (std=0 -> cv=0).

    HIGH=3, LOW=3: counts=[3,3], std=0, cv=0/3=0.
    """
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")] * 3
    result = class_severity_cv(problems)
    assert abs(result["A"]) < 1e-9, f"Uniform [3,3] -> cv=0.0; got {result['A']}"


def test_single_severity_zero_cv() -> None:
    """Single severity -> CV=0.0 (one bucket, std=0, cv=0)."""
    problems = [_p("A", "CRITICAL")] * 7
    result = class_severity_cv(problems)
    assert abs(result["A"]) < 1e-9, f"Single-severity -> cv=0.0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_cv([]) == {}


def test_three_severity_cv() -> None:
    """HIGH=3, MED=2, LOW=1: counts=[3,2,1], mean=2, std=sqrt(2/3), cv=sqrt(2/3)/2.

    variance = ((3-2)^2 + (2-2)^2 + (1-2)^2) / 3 = 2/3.
    std = sqrt(2/3).
    cv = sqrt(2/3) / 2.
    Kills impl with wrong formula or wrong normalization.
    """
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "MED")] * 2 + [_p("A", "LOW")]
    result = class_severity_cv(problems)
    expected = math.sqrt(2.0 / 3.0) / 2.0
    assert abs(result["A"] - expected) < 1e-9, (
        f"counts=[3,2,1], mean=2, std=sqrt(2/3), cv=sqrt(2/3)/2={expected:.6f}; got {result['A']}"
    )
