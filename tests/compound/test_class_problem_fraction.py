"""Item 276: class_problem_fraction() — fraction of total problems in a class (2026-06-08).

``class_problem_fraction(problems: list[Problem], cls: str) -> float``:
Returns count(cls) / len(problems): the fraction of ALL problems (across all classes)
that belong to *cls*. 0.0 when cls is absent or input is empty. Result in [0.0, 1.0].
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: denominator is global len(problems), not per-class count.
     A class with 3 of 5 problems has fraction 3/5=0.6, not 1.0.
     Kills impl using count(cls)/count(cls) = 1.0 always.
  2. 0.0 when cls absent.
     Kills impl that raises KeyError for absent cls.
  3. 0.0 on empty input.
     Kills impl that raises ZeroDivisionError.
  4. All fractions over all classes sum to 1.0.
     Verifies partition is consistent.
  5. Return type is float.
     Kills impl returning int or dict.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_problem_fraction,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_fraction_uses_global_denominator() -> None:
    """Denominator is global len(problems), not per-class count.

    PRIMARY DISCRIMINATOR: kills impl using count(cls)/count(cls)=1.0.
    alpha: 3 of 5 total -> fraction 3/5 = 0.6, not 1.0.
    """
    problems = [_p("alpha", i) for i in range(3)] + [_p("beta", i) for i in range(2)]
    result = class_problem_fraction(problems, "alpha")
    assert abs(result - 0.6) < 1e-9, f"alpha has 3/5 problems -> 0.6; got {result}"


def test_zero_when_cls_absent() -> None:
    """0.0 when cls is not present in problems.

    Kills impl that raises KeyError for absent class.
    """
    problems = [_p("alpha", 0), _p("alpha", 1)]
    result = class_problem_fraction(problems, "beta")
    assert result == 0.0, "beta absent -> 0.0; got " + repr(result)


def test_zero_on_empty_input() -> None:
    """0.0 on empty input without raising.

    Kills impl that raises ZeroDivisionError.
    """
    result = class_problem_fraction([], "alpha")
    assert result == 0.0, "Empty input -> 0.0; got " + repr(result)


def test_all_fractions_sum_to_one() -> None:
    """Sum of fractions over all classes equals 1.0.

    Verifies partition consistency.
    """
    problems = (
        [_p("alpha", i) for i in range(3)]
        + [_p("beta", i) for i in range(2)]
        + [_p("gamma", i) for i in range(5)]
    )
    total = sum(class_problem_fraction(problems, cls) for cls in ("alpha", "beta", "gamma"))
    assert abs(total - 1.0) < 1e-9, f"Fractions must sum to 1.0; got {total}"


def test_return_type_is_float() -> None:
    """Return type is float, not int or dict.

    Kills impl returning int.
    """
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = class_problem_fraction(problems, "alpha")
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
