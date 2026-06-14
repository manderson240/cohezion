"""Item 191: unique_problem_classes() — distinct-class set accessor (2026-06-08).

``unique_problem_classes(problems: list[Problem])`` → ``frozenset[str]``:
Returns the set of distinct ``problem_class`` values across all findings.
Empty list → ``frozenset()``.  Pure; no I/O.

Completes the trio:
  * ``finding_ids``          — IDs in insertion order
  * ``problem_classes``      — class labels in insertion order
  * ``unique_problem_classes`` — distinct-class frozenset

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: list with duplicate classes → only distinct classes returned.
     Kills an impl that preserves duplicates (e.g. delegates to problem_classes).
  2. Empty list → ``frozenset()`` (no raises, no None).
     Kills an impl that raises IndexError or returns an empty list.
  3. Return type is ``frozenset``, not ``set`` or ``list``.
     Kills an impl that returns a mutable set or a list.
  4. Known class present → found in result.
     Kills an impl that always returns the empty frozenset.
  5. Unknown class absent → not in result.
     Kills an impl that always returns all known template classes.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    unique_problem_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_duplicates_collapsed_to_distinct_set() -> None:
    """Duplicate problem_classes → only distinct values in result.

    PRIMARY DISCRIMINATOR: kills an impl that preserves duplicates (e.g. just
    calls problem_classes and wraps in frozenset only on the last step —
    which would still be correct, but also kills an impl that delegates to
    problem_classes without deduplication).
    'beta' appears twice; result must contain 'beta' exactly once.
    """
    problems = [
        _p("beta"),
        _p("alpha"),
        _p("beta", 1),
    ]

    result = unique_problem_classes(problems)

    assert result == frozenset({"beta", "alpha"}), (
        f"Distinct classes must be {{alpha, beta}}; got {result!r}"
    )


def test_empty_list_returns_empty_frozenset() -> None:
    """Empty list → frozenset() (no raises).

    Kills an impl that raises IndexError, returns None, or returns [].
    """
    result = unique_problem_classes([])

    assert result == frozenset(), f"Empty input must return frozenset(); got {result!r}"


def test_return_type_is_frozenset() -> None:
    """Return value is a frozenset, not a set or list.

    Kills an impl that returns a mutable set (which would make the caller
    unable to use the result as a dict key or in frozen contexts).
    """
    problems = [_p("complexity_outlier")]

    result = unique_problem_classes(problems)

    assert isinstance(result, frozenset), f"Return type must be frozenset; got {type(result)}"


def test_known_class_present_in_result() -> None:
    """A class that appears in the list must be present in the result.

    Kills an impl that always returns the empty frozenset regardless of input.
    """
    problems = [_p("nesting_outlier"), _p("long_function")]

    result = unique_problem_classes(problems)

    assert "nesting_outlier" in result, f"'nesting_outlier' must be in result; got {result!r}"
    assert "long_function" in result, f"'long_function' must be in result; got {result!r}"


def test_unknown_class_absent_from_result() -> None:
    """A class not in the input list must NOT appear in the result.

    Kills an impl that returns all known template classes regardless of
    which classes are actually present in the input list.
    """
    problems = [_p("complexity_outlier")]

    result = unique_problem_classes(problems)

    assert "nesting_outlier" not in result, (
        f"'nesting_outlier' must NOT be in result (not in input); got {result!r}"
    )
