"""Item 350: class_problem_ratio() -- ratio of class problems to total (2026-06-08).

``class_problem_ratio(problems, class_name) -> float``:
Returns count(class) / len(problems).  Unknown class -> 0.0.
Empty -> 0.0.  Result in [0.0, 1.0].  Pure; no I/O.
Complements problem_density_by_class for single-class lookups.

Discriminating tests:

  1. PRIMARY DISC.: returns a FLOAT ratio in [0.0, 1.0] not a percentage.
     Kills impl returning percentage (0-100) or an integer count.
  2. Known class returns correct fraction.
     Kills impl returning wrong arithmetic.
  3. Unknown class returns 0.0 not an error.
     Kills impl raising KeyError.
  4. Empty problems returns 0.0 not ZeroDivisionError.
     Kills impl dividing by zero.
  5. All-class input returns 1.0.
     Kills off-by-one in denominator.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_problem_ratio,
)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


def test_returns_float_ratio_not_percentage() -> None:
    """Returns float in [0.0, 1.0] not 0-100 percentage.

    PRIMARY DISCRIMINATOR: kills impl returning percentage or integer count.
    1 alpha out of 4 total -> 0.25 not 25.
    """
    problems = [_p("alpha", 0), _p("beta", 0), _p("beta", 1), _p("beta", 2)]
    result = class_problem_ratio(problems, "alpha")
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 0.25) < 1e-9, "1/4 = 0.25; got " + repr(result)
    assert 0.0 <= result <= 1.0, "Must be in [0,1]; got " + repr(result)


def test_known_class_correct_fraction() -> None:
    """Correct arithmetic: 3 alpha out of 5 total = 0.6."""
    problems = [_p("alpha", i) for i in range(3)] + [_p("beta", i) for i in range(2)]
    result = class_problem_ratio(problems, "alpha")
    assert abs(result - 0.6) < 1e-9, "3/5 = 0.6; got " + repr(result)


def test_unknown_class_returns_zero_not_error() -> None:
    """Unknown class_name returns 0.0 without raising KeyError."""
    problems = [_p("alpha", 0)]
    result = class_problem_ratio(problems, "UNKNOWN")
    assert result == 0.0, "unknown class -> 0.0; got " + repr(result)


def test_empty_problems_returns_zero() -> None:
    """Empty problems returns 0.0 (no ZeroDivisionError)."""
    result = class_problem_ratio([], "alpha")
    assert result == 0.0, "empty -> 0.0; got " + repr(result)


def test_all_class_problems_returns_one() -> None:
    """Class == all problems -> 1.0."""
    problems = [_p("alpha", i) for i in range(5)]
    result = class_problem_ratio(problems, "alpha")
    assert abs(result - 1.0) < 1e-9, "all alpha -> 1.0; got " + repr(result)
