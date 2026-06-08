"""Item 242: classes_above_count() — classes whose count strictly exceeds n (2026-06-08).

``classes_above_count(problems: list[Problem], n: int) -> frozenset[str]``:
Returns the frozenset of class names whose problem count is strictly greater
than ``n``.  Classes with count ≤ n are excluded.  Passing n=0 returns all
non-empty classes.  Empty input → frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: classes with count ≤ n are excluded (kills an impl that
     returns all classes regardless of count).
  2. A class with count exactly equal to n is excluded (boundary).
     Kills an impl using ≥ instead of >.
  3. n=0 returns all non-empty classes.
     Kills an impl that mishandles zero threshold.
  4. Empty input → frozenset().
     Kills an impl that raises or returns None.
  5. Return type is frozenset, not list or dict.
     Kills an impl returning a list or dict.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_above_count,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_classes_at_or_below_n_excluded() -> None:
    """Classes with count ≤ n are not returned.

    PRIMARY DISCRIMINATOR: kills an impl that returns all classes.
    alpha has count=2 (> 3? No).  With n=3, alpha (count=2) must be excluded.
    """
    problems = [_p("alpha", 0), _p("alpha", 1)]  # count=2
    result = classes_above_count(problems, n=3)
    assert "alpha" not in result, (
        "alpha has count=2 which is ≤ 3; must be excluded; got " + repr(result)
    )
    assert len(result) == 0, "No class exceeds n=3; result must be empty; got " + repr(result)


def test_count_exactly_n_excluded() -> None:
    """A class with count exactly equal to n is NOT returned (strictly greater).

    Kills an impl using >= instead of >.
    """
    problems = [_p("beta", 0), _p("beta", 1), _p("beta", 2)]  # count=3
    result = classes_above_count(problems, n=3)
    assert "beta" not in result, (
        "beta has count=3 which equals n=3; must be excluded (strictly >); got " + repr(result)
    )


def test_n_zero_returns_all_nonempty_classes() -> None:
    """n=0 returns all classes that have at least one problem.

    Kills an impl that mishandles n=0 (e.g. returns empty).
    """
    problems = [_p("alpha"), _p("beta"), _p("gamma")]
    result = classes_above_count(problems, n=0)
    assert result == frozenset({"alpha", "beta", "gamma"}), (
        "n=0 → all 3 classes returned; got " + repr(result)
    )


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty problems → frozenset().

    Kills an impl that raises or returns None.
    """
    result = classes_above_count([], n=1)
    assert result == frozenset(), "Empty input → frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset, not list or dict.

    Kills an impl returning a list or dict.
    """
    problems = [_p("x", 0), _p("x", 1), _p("x", 2)]  # count=3
    result = classes_above_count(problems, n=1)
    assert isinstance(result, frozenset), (
        "Must return frozenset; got " + repr(type(result))
    )
    assert "x" in result, "x has count=3 > n=1; must be included; got " + repr(result)
