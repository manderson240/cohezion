"""Item 262: problems_in_class() — retrieve all problems for a given class (2026-06-08).

``problems_in_class(problems, cls) -> list[Problem]``:
Returns all Problem instances whose ``problem_class`` equals ``cls``, in the
same order they appear in the input.  Empty list when the class is absent or
input is empty.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: filters to exactly ``cls``; problems from other classes
     are excluded.  Kills impl returning all problems regardless of cls.
  2. Input order is preserved among returned problems.
     Kills impl that sorts or re-orders the output.
  3. Empty list when the class is absent.
     Kills impl that raises KeyError on a missing class.
  4. Empty list on empty input.
     Kills impl that raises on empty input.
  5. Return type is list[Problem] (not a count, frozenset, or dict).
     Kills impl returning len() or a set.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_in_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_filters_to_exactly_cls() -> None:
    """Returns only problems from the target class; others excluded.

    PRIMARY DISCRIMINATOR: kills impl that ignores cls and returns all problems.
    alpha has 3 problems, beta has 2.  Asking for alpha returns only alpha's 3.
    """
    alpha = [_ps("alpha", i) for i in range(3)]
    beta = [_ps("beta", i) for i in range(2)]
    result = problems_in_class(alpha + beta, "alpha")
    assert result == alpha, "Only alpha's 3 problems; got " + repr(result)
    assert all(p.problem_class == "alpha" for p in result), (
        "All returned problems must be from class 'alpha'"
    )


def test_input_order_preserved() -> None:
    """Returned problems are in the same order as in the input.

    Kills impl that sorts or reverses the output.
    """
    p_z = Problem(problem_class="alpha", finding_id="alpha:z")
    p_a = Problem(problem_class="alpha", finding_id="alpha:a")
    p_m = Problem(problem_class="alpha", finding_id="alpha:m")
    result = problems_in_class([p_z, p_a, p_m], "alpha")
    assert [p.finding_id for p in result] == ["alpha:z", "alpha:a", "alpha:m"], (
        "Input order preserved; got " + repr([p.finding_id for p in result])
    )


def test_empty_list_when_class_absent() -> None:
    """Returns [] when no problem belongs to cls.

    Kills impl that raises KeyError for a missing class.
    """
    problems = [_ps("beta", i) for i in range(3)]
    result = problems_in_class(problems, "alpha")
    assert result == [], "alpha absent -> []; got " + repr(result)


def test_empty_list_on_empty_input() -> None:
    """Returns [] on empty input.

    Kills impl that raises on empty input.
    """
    result = problems_in_class([], "alpha")
    assert result == [], "Empty input -> []; got " + repr(result)


def test_return_type_is_list_of_problems() -> None:
    """Return type is list[Problem], not a count or frozenset.

    Kills impl returning len() or a frozenset of finding_ids.
    """
    problems = [_ps("alpha", 0), _ps("alpha", 1)]
    result = problems_in_class(problems, "alpha")
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert all(isinstance(p, Problem) for p in result), "Elements must be Problem instances"
    assert len(result) == 2
