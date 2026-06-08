"""Item 216: top_k_classes() — top-K most frequent classes (2026-06-08).

``top_k_classes(problems: list[Problem], k: int) -> list[str]``
Returns up to *k* problem_class names in descending count order.
Ties broken by first occurrence in the input list.
k <= 0 -> [].  empty problems -> [].  fewer than k classes -> all of them.
Pure; no I/O.

Generalises most_common_class() from a scalar to a ranked list::

    top = top_k_classes(findings, 3)   # worst 3 categories

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: k=1 returns [class_name], NOT [count].
     Kills an impl that returns counts in place of class names.
  2. Descending count order -- highest first.
     Kills an impl that returns ascending or alphabetical order.
  3. Tie broken by first occurrence (not alphabetical).
     Kills an impl that uses alphabetical tie-breaking.
  4. k > distinct classes -> all classes returned (no padding, no error).
     Kills an impl that raises when k > len(distinct).
  5. k <= 0 -> empty list; empty problems -> empty list.
     Kills an impl that returns None or raises on degenerate inputs.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_k_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_k1_returns_class_name_not_count() -> None:
    """k=1 returns the class name string, NOT the count integer.

    PRIMARY DISCRIMINATOR: kills an impl that returns counts.
    alpha appears 3 times, beta 1 time -> top_k_classes(problems, 1) == ["alpha"].
    """
    problems = [_p("alpha", i) for i in range(3)] + [_p("beta")]
    result = top_k_classes(problems, 1)
    assert result == ["alpha"], "k=1 must return [class_name]; got " + repr(result)


def test_descending_count_order() -> None:
    """Classes returned highest-count first.

    Kills an impl that returns ascending or alphabetical order.
    gamma=4, alpha=3, beta=2 -> ["gamma", "alpha", "beta"].
    """
    problems = (
        [_p("gamma", i) for i in range(4)]
        + [_p("alpha", i) for i in range(3)]
        + [_p("beta", i) for i in range(2)]
    )
    result = top_k_classes(problems, 3)
    assert result == ["gamma", "alpha", "beta"], "Must be in descending count order; got " + repr(
        result
    )


def test_tie_broken_by_first_occurrence() -> None:
    """Equal counts resolved by first-seen order in the input list.

    Kills an impl that uses alphabetical tie-breaking.
    beta appears before alpha in the list; both have count=2 -> ["beta", "alpha"].
    """
    problems = [_p("beta", 0), _p("beta", 1), _p("alpha", 0), _p("alpha", 1)]
    result = top_k_classes(problems, 2)
    assert result == ["beta", "alpha"], "Tie must be broken by first occurrence; got " + repr(
        result
    )


def test_k_larger_than_distinct_classes() -> None:
    """k > number of distinct classes -> return all classes (no error).

    Kills an impl that raises IndexError or pads with None/empty strings.
    """
    problems = [_p("alpha", i) for i in range(2)] + [_p("beta")]
    result = top_k_classes(problems, 10)
    assert set(result) == {"alpha", "beta"}, "k > classes must return all classes; got " + repr(
        result
    )
    assert len(result) == 2, "No padding; got " + repr(result)


def test_degenerate_inputs_return_empty_list() -> None:
    """k <= 0 or empty problems both return [].

    Kills an impl that returns None or raises on degenerate inputs.
    """
    problems = [_p("alpha")]
    assert top_k_classes(problems, 0) == [], "k=0 must return []"
    assert top_k_classes(problems, -5) == [], "k=-5 must return []"
    assert top_k_classes([], 3) == [], "empty problems must return []"
