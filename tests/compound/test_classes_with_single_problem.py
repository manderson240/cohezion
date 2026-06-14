"""Item 241: classes_with_single_problem() — classes with exactly one problem (2026-06-08).

``classes_with_single_problem(problems: list[Problem]) -> frozenset[str]``:
Returns the frozenset of class names that appear exactly once in *problems*.
Classes with 0 or ≥2 occurrences are excluded.
Empty input → empty frozenset.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: a class with count=2 is excluded (kills an impl that
     returns all non-empty classes, i.e. classes with count≥1).
  2. A class with count=1 is included.
     Kills an impl that only returns empty-or-all logic.
  3. Empty input → frozenset().
     Kills an impl that raises or returns None.
  4. Return type is frozenset, not list or dict.
     Kills an impl returning a list or dict.
  5. Multiple classes: only the singleton ones are returned.
     Kills an impl that returns all classes regardless of count.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
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


def test_class_with_count_two_excluded() -> None:
    """A class with exactly 2 problems is NOT returned.

    PRIMARY DISCRIMINATOR: kills an impl that returns all classes with
    count ≥ 1 (i.e. classes_with_problems()).
    alpha has 2 problems; result must be empty.
    """
    problems = [_p("alpha", 0), _p("alpha", 1)]
    result = classes_with_single_problem(problems)
    assert "alpha" not in result, "alpha has count=2, must be excluded; got " + repr(result)
    assert len(result) == 0, "Only alpha exists with count=2; result must be empty; got " + repr(
        result
    )


def test_class_with_count_one_included() -> None:
    """A class with exactly 1 problem IS returned.

    Kills an impl that always returns the empty set.
    """
    problems = [_p("beta", 0)]
    result = classes_with_single_problem(problems)
    assert "beta" in result, "beta has count=1, must be included; got " + repr(result)


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty problems → frozenset().

    Kills an impl that raises or returns None.
    """
    result = classes_with_single_problem([])
    assert result == frozenset(), "Empty input → frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset, not list or dict.

    Kills an impl returning a list or dict.
    """
    result = classes_with_single_problem([_p("gamma")])
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))


def test_only_singleton_classes_returned_mixed_counts() -> None:
    """Multiple classes: only the ones with count=1 are returned.

    Kills an impl that returns all class names regardless of count.
    alpha has 3 problems, beta has 1, gamma has 2, delta has 1.
    Only beta and delta should appear.
    """
    problems = [
        _p("alpha", 0),
        _p("alpha", 1),
        _p("alpha", 2),
        _p("beta", 0),
        _p("gamma", 0),
        _p("gamma", 1),
        _p("delta", 0),
    ]
    result = classes_with_single_problem(problems)
    assert result == frozenset({"beta", "delta"}), "Only beta and delta have count=1; got " + repr(
        result
    )
