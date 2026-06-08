"""Item 243: classes_below_count() — classes whose count is strictly < n (2026-06-08).

``classes_below_count(problems: list[Problem], n: int) -> frozenset[str]``:
Returns the frozenset of class names whose problem count is strictly less than
``n``.  Only classes actually present in the scan are considered (count ≥ 1).
So n=1 always returns frozenset() because every present class has count ≥ 1.
n=2 returns the same result as ``classes_with_single_problem()``.
Empty input → frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: classes with count ≥ n are excluded (kills impl that
     returns all present classes).
  2. n=1 always returns frozenset() — every present class has count ≥ 1.
     Kills an impl that incorrectly includes present classes for n=1.
  3. n=2 returns the same set as classes_with_single_problem().
     Kills an impl that uses ≤ instead of <.
  4. Empty input → frozenset().
     Kills an impl that raises or returns None.
  5. Return type is frozenset, not list or dict.
     Kills an impl returning a list or dict.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_below_count,
    classes_with_single_problem,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_classes_at_or_above_n_excluded() -> None:
    """Classes with count ≥ n are not returned.

    PRIMARY DISCRIMINATOR: kills an impl that returns all present classes.
    alpha has count=3, beta has count=1.  With n=2, only beta (count=1) qualifies.
    """
    problems = [
        _p("alpha", 0), _p("alpha", 1), _p("alpha", 2),  # count=3
        _p("beta", 0),                                     # count=1
    ]
    result = classes_below_count(problems, n=2)
    assert "alpha" not in result, (
        "alpha has count=3 ≥ n=2; must be excluded; got " + repr(result)
    )
    assert "beta" in result, (
        "beta has count=1 < n=2; must be included; got " + repr(result)
    )


def test_n_one_always_returns_empty() -> None:
    """n=1 → frozenset() because every present class has count ≥ 1.

    Kills an impl that incorrectly includes present classes for n=1.
    """
    problems = [_p("alpha"), _p("beta"), _p("gamma")]
    result = classes_below_count(problems, n=1)
    assert result == frozenset(), (
        "n=1 → every class has count ≥ 1, so result must be frozenset(); got "
        + repr(result)
    )


def test_n_two_agrees_with_classes_with_single_problem() -> None:
    """n=2 returns the same frozenset as classes_with_single_problem().

    Kills an impl that uses ≤ instead of <.
    alpha has count=2 (excluded), beta has count=1 (included).
    """
    problems = [_p("alpha", 0), _p("alpha", 1), _p("beta", 0)]
    assert classes_below_count(problems, n=2) == classes_with_single_problem(problems), (
        "n=2 must agree with classes_with_single_problem()"
    )


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty problems → frozenset().

    Kills an impl that raises or returns None.
    """
    result = classes_below_count([], n=5)
    assert result == frozenset(), "Empty input → frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset, not list or dict.

    Kills an impl returning a list or dict.
    """
    result = classes_below_count([_p("x")], n=3)
    assert isinstance(result, frozenset), (
        "Must return frozenset; got " + repr(type(result))
    )
    assert "x" in result, "x has count=1 < n=3; must be included; got " + repr(result)
