"""Item 274: classes_above_problem_count() — classes meeting a minimum count threshold (2026-06-08).

``classes_above_problem_count(problems: list[Problem], min_count: int) -> frozenset[str]``:
Returns the frozenset of class names whose total problem count is >= min_count.
Empty input or no class meeting the threshold → frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only classes meeting >= min_count are returned.
     Kills impl returning ALL classes regardless of count, or using strict >
     instead of >=.
  2. min_count=1 returns all classes that have at least one problem.
     Verifies the inclusive lower boundary and confirms ALL classes present.
  3. min_count above any class count returns frozenset() (empty).
     Kills impl that always includes at least one class.
  4. Empty input returns frozenset() without raising.
     Kills impl that raises ZeroDivisionError or KeyError on empty.
  5. Return type is frozenset.
     Kills impl returning list, set, or tuple.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_above_problem_count,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_only_classes_meeting_threshold() -> None:
    """Only classes with total count >= min_count are returned.

    PRIMARY DISCRIMINATOR: kills impl returning all classes or using >.
    alpha: 1 problem; beta: 3 problems; gamma: 2 problems.
    min_count=2 → beta (3) + gamma (2). alpha (1) must be excluded.
    """
    problems = [
        _p("alpha", 0),
        _p("beta", 0),
        _p("beta", 1),
        _p("beta", 2),
        _p("gamma", 0),
        _p("gamma", 1),
    ]
    result = classes_above_problem_count(problems, min_count=2)
    assert "beta" in result, "beta has 3 >= 2; must be included"
    assert "gamma" in result, "gamma has 2 >= 2; must be included (inclusive)"
    assert "alpha" not in result, "alpha has 1 < 2; must be excluded"


def test_min_count_one_returns_all_classes() -> None:
    """min_count=1 returns all classes that have any problems.

    Verifies the inclusive lower bound: every class present in problems
    has at least 1 problem, so all must be returned.
    """
    problems = [_p("alpha", 0), _p("beta", 0), _p("gamma", 0)]
    result = classes_above_problem_count(problems, min_count=1)
    assert result == frozenset({"alpha", "beta", "gamma"}), (
        "min_count=1 must return all classes; got " + repr(result)
    )


def test_min_count_above_all_returns_empty() -> None:
    """min_count exceeding all class counts returns frozenset().

    Kills impl that always includes at least the top class.
    """
    problems = [_p("alpha", 0), _p("alpha", 1)]  # alpha has 2 problems
    result = classes_above_problem_count(problems, min_count=10)
    assert result == frozenset(), "No class has 10 problems; must return frozenset(); got " + repr(
        result
    )


def test_empty_input_returns_frozenset() -> None:
    """Empty input returns frozenset() without raising.

    Kills impl that raises or returns None on empty.
    """
    result = classes_above_problem_count([], min_count=1)
    assert result == frozenset(), "Empty input → frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset (not list, set, or tuple).

    Kills impl returning the wrong collection type.
    """
    result = classes_above_problem_count([_p("alpha", 0)], min_count=1)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
