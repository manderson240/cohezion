"""Item 288: class_co_occurrence_count() — how many finding_ids two classes share (2026-06-08).

``class_co_occurrence_count(problems: list[Problem], cls_a: str, cls_b: str) -> int``:
Returns |{ids in cls_a} ∩ {ids in cls_b}|.  0 if either class is absent or empty input.
cls_a == cls_b → count = number of distinct finding_ids in that class.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts distinct finding_ids, not Problem instances.
     Kills impl that counts Problem objects (would over-count duplicates).
  2. One class absent -> 0 (no KeyError).
     Kills impl that raises on missing class.
  3. cls_a == cls_b -> count equals unique ids in that class.
     Kills impl that returns 0 for identical inputs.
  4. Empty input -> 0 without raising.
     Kills impl raising on empty.
  5. Return type is int (not frozenset or list).
     Kills impl returning the intersection set itself.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_co_occurrence_count,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_counts_distinct_finding_ids_not_problems() -> None:
    """Counts distinct finding_ids in the intersection, not Problem instances.

    PRIMARY DISCRIMINATOR: kills impl that counts Problem objects.
    'shared' appears twice in alpha (two Problem records with same id) and
    once in beta -> intersection has 1 distinct id, count = 1.
    """
    problems = [
        _p("alpha", "shared"),
        _p("alpha", "shared"),  # duplicate finding_id in alpha
        _p("beta", "shared"),
        _p("alpha", "only_alpha"),
    ]
    result = class_co_occurrence_count(problems, "alpha", "beta")
    assert result == 1, (
        "Intersection has 1 distinct id ('shared'), not 2 Problem objects; got "
        + repr(result)
    )


def test_absent_class_returns_zero() -> None:
    """One class absent -> 0, not an exception.

    Kills impl raising KeyError or IndexError on missing class.
    """
    problems = [_p("alpha", "id1"), _p("alpha", "id2")]
    result = class_co_occurrence_count(problems, "alpha", "missing")
    assert result == 0, (
        "'missing' class absent -> 0; got " + repr(result)
    )


def test_same_class_returns_unique_count() -> None:
    """cls_a == cls_b -> count equals the number of unique ids in that class.

    Kills impl that returns 0 for identical inputs (treating it as 'no overlap').
    alpha has 2 distinct ids -> count = 2.
    """
    problems = [
        _p("alpha", "id1"),
        _p("alpha", "id2"),
        _p("beta", "id3"),
    ]
    result = class_co_occurrence_count(problems, "alpha", "alpha")
    assert result == 2, (
        "alpha has 2 distinct ids; alpha ∩ alpha = 2; got " + repr(result)
    )


def test_empty_input_returns_zero() -> None:
    """Empty input -> 0 without raising.

    Kills impl raising on empty list.
    """
    result = class_co_occurrence_count([], "alpha", "beta")
    assert result == 0, "Empty input -> 0; got " + repr(result)


def test_return_type_is_int() -> None:
    """Return type is int, not frozenset or list.

    Kills impl returning the intersection object itself.
    """
    problems = [_p("alpha", "shared"), _p("beta", "shared")]
    result = class_co_occurrence_count(problems, "alpha", "beta")
    assert isinstance(result, int), (
        "Must return int; got " + repr(type(result))
    )
    assert result == 1, "One shared id -> 1; got " + repr(result)
