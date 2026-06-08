"""Item 280: severity_gini() — Gini impurity of severity distribution (2026-06-08).

``severity_gini(problems: list[Problem]) -> float``:
Returns the Gini impurity of the labelled severity distribution:
  1.0 - sum((count_i / total_labelled)^2) over non-empty severities.
Range: 0.0 (single severity, pure) to (1 - 1/k) (k equal-frequency severities).
0.0 on empty input or all-unlabelled. Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: formula is Gini (1 - sum(p^2)), not Shannon entropy.
     For 1 HIGH + 1 LOW (p=0.5 each): Gini = 1 - (0.25+0.25) = 0.5.
     Shannon would give 1.0. Kills impl using Shannon formula.
  2. Pure distribution (single severity) -> Gini = 0.0.
     Kills impl not handling mono-severity case.
  3. Unlabelled problems excluded from denominator.
     Kills impl including severity='' in the count.
  4. 0.0 on empty input.
     Kills impl raising ZeroDivisionError.
  5. Return type is float in [0.0, 1.0].
     Kills impl returning an int or a dict.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import (
    Problem,
    severity_gini,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_gini_formula_not_entropy() -> None:
    """Formula is 1 - sum(p^2), NOT Shannon entropy.

    PRIMARY DISCRIMINATOR: kills impl using -sum(p*log2(p)).
    1 HIGH + 1 LOW: p=0.5 each.
    Gini  = 1 - (0.25 + 0.25) = 0.5
    Shannon would give 1.0 (completely different value).
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "LOW")]
    result = severity_gini(problems)
    assert abs(result - 0.5) < 1e-9, (
        f"1 HIGH + 1 LOW -> Gini=0.5; got {result} (Shannon would be 1.0)"
    )


def test_mono_severity_gives_zero() -> None:
    """Single-severity distribution -> Gini = 0.0 (pure, no impurity).

    Kills impl not handling mono-severity case.
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(5)]
    result = severity_gini(problems)
    assert result == 0.0, f"All HIGH -> Gini=0.0; got {result}"


def test_unlabelled_excluded_from_denominator() -> None:
    """Unlabelled (severity='') problems excluded from Gini calculation.

    Kills impl including '' in the denominator.
    2 HIGH + 2 LOW + 10 unlabelled. Only labelled (4 total) used:
    p_HIGH = 0.5, p_LOW = 0.5 -> Gini = 0.5 (not 0.5 * 4/14 = 0.143).
    """
    problems = (
        [_ps("alpha", i, "HIGH") for i in range(2)]
        + [_ps("beta", i, "LOW") for i in range(2)]
        + [_p("gamma", i) for i in range(10)]
    )
    result = severity_gini(problems)
    assert abs(result - 0.5) < 1e-9, (
        f"2 HIGH + 2 LOW (unlabelled excluded) -> Gini=0.5; got {result}"
    )


def test_zero_on_empty_input() -> None:
    """0.0 on empty input without raising.

    Kills impl raising ZeroDivisionError.
    """
    result = severity_gini([])
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_return_type_is_float() -> None:
    """Return type is float, not int or dict.

    Kills impl returning an int.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "LOW")]
    result = severity_gini(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # Also check 0 <= result <= 1
    assert 0.0 <= result <= 1.0, f"Gini must be in [0, 1]; got {result}"
