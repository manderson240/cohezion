"""Item 256: any_class_above_severity_fraction() — per-class severity gate (2026-06-08).

``any_class_above_severity_fraction(problems: list[Problem], severity: str,
min_fraction: float) -> bool``:
Returns ``True`` if at least one class has a fraction of its own problems at
*severity* that is ``>=`` *min_fraction*.  The denominator is the total count
of that class's problems (all severities + unlabelled).  This is a per-class
check, NOT the global ``severity_fraction()``.  Returns ``False`` when no
class meets the threshold or when there are no problems.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: uses per-class denominator (total problems in that class),
     NOT the global denominator (all labelled problems).  Kills impl that calls
     severity_fraction(all_problems, severity) and compares with min_fraction.
  2. Returns False when no class meets the threshold.
     Kills impl that always returns True when labelled problems exist.
  3. Boundary is >= (inclusive) — True when fraction exactly equals min_fraction.
     Kills impl using strictly > (the inverse boundary of item 251).
  4. Returns False when no problems are present.
     Kills impl that raises on empty input.
  5. Return type is bool, not float or int.
     Kills impl returning the fraction or a count.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    any_class_above_severity_fraction,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_per_class_not_global_fraction() -> None:
    """Uses per-class denominator, not the global severity fraction.

    PRIMARY DISCRIMINATOR: alpha has 1/1 HIGH (100% per-class), but globally
    HIGH is 1/100 (1% — far below min_fraction=0.5).  Must return True because
    alpha's per-class fraction exceeds the threshold.
    """
    # alpha: 1 HIGH (100% of alpha's problems)
    alpha_problems = [_ps("alpha", 0, "HIGH")]
    # beta: 99 LOW problems (no HIGH)
    beta_problems = [_ps("beta", i, "LOW") for i in range(99)]
    problems = alpha_problems + beta_problems
    # Globally: 1/1 labelled HIGH, 99 LOW → global HIGH fraction = 1/(1+99)=0.01
    # But per-class: alpha=1/1=1.0 ≥ 0.5 → True
    result = any_class_above_severity_fraction(problems, "HIGH", 0.5)
    assert result is True, (
        "alpha has 100% HIGH per-class → True; global fraction is 1% but "
        "per-class is checked; got " + repr(result)
    )


def test_false_when_no_class_meets_threshold() -> None:
    """Returns False when no class has a fraction >= min_fraction.

    Kills impl that returns True whenever labelled problems exist.
    alpha: 1 HIGH / 10 total = 10% < min_fraction=50%.
    """
    problems = [_ps("alpha", 0, "HIGH")] + [_ps("alpha", i + 1, "LOW") for i in range(9)]
    result = any_class_above_severity_fraction(problems, "HIGH", 0.5)
    assert result is False, "alpha 1/10 HIGH = 10% < 50% → False; got " + repr(result)


def test_inclusive_boundary_at_exact_fraction() -> None:
    """Returns True when a class's fraction exactly equals min_fraction (>= boundary).

    Kills impl that uses strictly > (which would return False at equality).
    alpha: 1 HIGH / 2 total = 0.5.  min_fraction=0.5 → True (inclusive).
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "LOW")]
    result = any_class_above_severity_fraction(problems, "HIGH", 0.5)
    assert result is True, "alpha 1/2=0.5 >= 0.5 → True (inclusive boundary); got " + repr(result)


def test_false_when_no_problems() -> None:
    """Returns False when problems list is empty.

    Kills impl that raises on empty input.
    """
    result = any_class_above_severity_fraction([], "HIGH", 0.5)
    assert result is False, "Empty problems → False; got " + repr(result)


def test_return_type_is_bool() -> None:
    """Return type is bool.

    Kills impl returning float (the fraction) or int.
    """
    result = any_class_above_severity_fraction([_ps("alpha", 0, "HIGH")], "HIGH", 0.5)
    assert isinstance(result, bool), "Must return bool; got " + repr(type(result))
