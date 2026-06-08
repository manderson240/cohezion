"""Item 190: problem_classes() — insertion-order class extraction (2026-06-08).

``problem_classes(problems: list[Problem])`` → ``list[str]``:
Returns the ``problem_class`` values of all findings in *problems*, in
insertion order, with duplicates preserved.  Empty list → ``[]``.
Pure; no I/O.

Enables::

    set(problem_classes(findings))      # distinct class names
    Counter(problem_classes(findings))  # alternative to problem_count_by_class

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: mixed list → classes in insertion order (not sorted, not distinct).
     Kills an impl that returns only distinct classes or sorts them.
  2. Empty list → ``[]`` (no raises).
     Kills an impl that raises on empty input.
  3. Duplicates preserved (not deduplicated).
     Kills an impl that deduplicates via set() before returning.
  4. Result contains strings, not Problem instances.
     Kills an impl that returns Problem objects instead of their class strings.
  5. Single-element list → ``[that problem_class]``.
     Kills an impl that returns ``[]`` for single-element input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problem_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_insertion_order_with_duplicates() -> None:
    """Mixed list → class names in insertion order, duplicates preserved.

    PRIMARY DISCRIMINATOR: kills an impl that returns only distinct classes
    (e.g. via set), or that sorts the result.
    'alpha' appears twice; both occurrences must be in the result, in order.
    """
    problems = [
        _p("beta"),
        _p("alpha", 0),
        _p("beta", 1),
        _p("alpha", 1),
    ]

    result = problem_classes(problems)

    assert result == ["beta", "alpha", "beta", "alpha"], (
        f"Insertion order with duplicates must be preserved; got {result!r}"
    )


def test_empty_list_returns_empty() -> None:
    """Empty list → [] (no raises).

    Kills an impl that raises IndexError or returns None on empty input.
    """
    result = problem_classes([])

    assert result == [], f"Empty input must return []; got {result!r}"


def test_duplicates_preserved() -> None:
    """Duplicate problem_classes kept (not deduplicated via set()).

    Kills an impl that calls set() before returning, silently dropping
    duplicates and changing the length.
    """
    problems = [_p("complexity_outlier"), _p("complexity_outlier", 1)]

    result = problem_classes(problems)

    assert len(result) == 2, f"Duplicates must be preserved; got {result!r}"
    assert result == ["complexity_outlier", "complexity_outlier"], (
        f"Both class values must appear; got {result!r}"
    )


def test_result_contains_strings_not_problems() -> None:
    """Result elements are strings (problem_class values), not Problem instances.

    Kills an impl that returns the Problem objects themselves instead of
    extracting the problem_class attribute.
    """
    problems = [_p("nesting_outlier")]

    result = problem_classes(problems)

    assert len(result) == 1
    assert isinstance(result[0], str), (
        f"Elements must be str; got {type(result[0])} for {result[0]!r}"
    )
    assert result[0] == "nesting_outlier", f"String must be the problem_class; got {result[0]!r}"


def test_single_element_returns_list_of_one_class() -> None:
    """Single-element list → [that problem_class].

    Kills an impl that requires ≥2 elements to return a non-empty result.
    """
    result = problem_classes([_p("compound_smell")])

    assert result == ["compound_smell"], f"Single element must return [class]; got {result!r}"
