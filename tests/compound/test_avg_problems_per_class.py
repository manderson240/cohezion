"""Item 840: avg_problems_per_class() -- global average problems per distinct class.

avg_problems_per_class(problems) -> float.
= len(problems) / count_distinct_classes. Empty -> 0.0. Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: total/distinct_classes float (kills total=6 int; fraction=2/6 wrong);
     6 problems across 2 classes -> 3.0.
  2. Single class many problems -> density = n (all in one class).
  3. One problem per class -> density = 1.0.
  4. Empty -> 0.0 (no ZeroDivision).
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, avg_problems_per_class


def _p(cls: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity="HIGH")


def test_density_not_total_not_fraction_primary_discriminator() -> None:
    """PRIMARY DISC.: 6 problems / 2 classes = 3.0; total=6 wrong; 2/6=0.33 wrong."""
    problems = [_p("A")] * 4 + [_p("B")] * 2
    got = avg_problems_per_class(problems)
    assert math.isclose(got, 3.0, abs_tol=1e-9), f"expected 3.0; got {got}"
    assert not math.isclose(got, 6.0, abs_tol=1e-6), "Must not return total"
    assert isinstance(got, float)


def test_single_class_density_equals_count() -> None:
    """All problems in one class -> density = total."""
    problems = [_p("A")] * 5
    got = avg_problems_per_class(problems)
    assert math.isclose(got, 5.0, abs_tol=1e-9)


def test_one_per_class_gives_one() -> None:
    """One problem per class -> density = 1.0."""
    problems = [_p("A"), _p("B"), _p("C")]
    got = avg_problems_per_class(problems)
    assert math.isclose(got, 1.0, abs_tol=1e-9)


def test_empty_returns_zero() -> None:
    """Empty -> 0.0 (no ZeroDivision)."""
    assert avg_problems_per_class([]) == 0.0


def test_return_type_is_float() -> None:
    """Result must be float."""
    problems = [_p("A"), _p("B")]
    assert isinstance(avg_problems_per_class(problems), float)
