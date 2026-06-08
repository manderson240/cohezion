"""Item 314: problem_class_pairs() — all unordered pairs of co-occurring classes (2026-06-08).

``problem_class_pairs(problems) -> frozenset[frozenset[str]]``:
Returns the frozenset of all unordered 2-element class pairs that co-occur in the scan.
Each pair is represented as a frozenset{a, b} so order does not matter.
Classes with zero problems excluded.
Fewer than 2 distinct classes -> frozenset().
Empty -> frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: each pair appears EXACTLY ONCE as an unordered frozenset.
     Kills impl returning ordered tuples or duplicate pairs (both (a,b) and (b,a)).
  2. 3 distinct classes -> exactly 3 pairs (nC2 = 3).
     Kills impl with wrong count or missing pairs.
  3. Single class -> frozenset() (no pairs possible with 1 class).
     Kills impl returning a singleton frozenset or pairing a class with itself.
  4. Empty input -> frozenset().
     Kills impl that crashes or returns non-empty.
  5. Return type is frozenset containing frozensets of strings.
     Kills impl returning set of tuples or list of lists.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problem_class_pairs,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pairs_are_unordered_frozensets_appearing_exactly_once() -> None:
    """Each pair is a frozenset (unordered) and appears exactly once.

    PRIMARY DISCRIMINATOR: kills impl returning ordered tuples or both (a,b)+(b,a).
    alpha and beta -> one pair: frozenset({'alpha','beta'}).
    NOT two pairs like ('alpha','beta') and ('beta','alpha').
    """
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = problem_class_pairs(problems)
    assert frozenset({"alpha", "beta"}) in result, (
        "frozenset({'alpha','beta'}) in result; got " + repr(result)
    )
    assert len(result) == 1, "exactly 1 pair for 2 classes; got " + repr(result)


def test_three_classes_produce_three_pairs() -> None:
    """3 distinct classes -> exactly 3 pairs (C(3,2) = 3).

    Kills impl with wrong count or missing pairs.
    alpha, beta, gamma -> {alpha,beta}, {alpha,gamma}, {beta,gamma}.
    """
    problems = [_p("alpha", 0), _p("beta", 0), _p("gamma", 0)]
    result = problem_class_pairs(problems)
    assert len(result) == 3, "3 classes -> 3 pairs; got " + repr(result)
    assert frozenset({"alpha", "beta"}) in result, "alpha-beta pair missing"
    assert frozenset({"alpha", "gamma"}) in result, "alpha-gamma pair missing"
    assert frozenset({"beta", "gamma"}) in result, "beta-gamma pair missing"


def test_single_class_returns_empty_frozenset() -> None:
    """Single distinct class -> frozenset() (no valid pair exists).

    Kills impl returning a singleton or pairing class with itself.
    """
    problems = [_p("alpha", 0), _p("alpha", 1), _p("alpha", 2)]
    result = problem_class_pairs(problems)
    assert result == frozenset(), "single class -> frozenset(); got " + repr(result)


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input -> frozenset().

    Kills impl that crashes or returns non-empty.
    """
    result = problem_class_pairs([])
    assert result == frozenset(), "empty -> frozenset(); got " + repr(result)


def test_return_type_is_frozenset_of_frozensets() -> None:
    """Return type is frozenset containing frozensets of strings.

    Kills impl returning set of tuples or list of lists.
    """
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = problem_class_pairs(problems)
    assert isinstance(result, frozenset), (
        "Outer must be frozenset; got " + repr(type(result))
    )
    for pair in result:
        assert isinstance(pair, frozenset), (
            "Each pair must be frozenset; got " + repr(type(pair))
        )
        assert len(pair) == 2, "Each pair has exactly 2 elements; got " + repr(pair)
