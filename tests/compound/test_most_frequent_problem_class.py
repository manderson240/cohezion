"""Item 177: most_frequent_problem_class() — top class by finding count (2026-06-08).

``most_frequent_problem_class(problems: list[Problem])`` → ``str | None``:
Returns the ``problem_class`` name with the highest finding count.
Ties are broken alphabetically.  Empty input → ``None``.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: clear winner → that class name returned (not another class).
     Kills an impl that always returns the first class seen regardless of count.
  2. Tie broken alphabetically (ascending) — earlier class wins a tie.
     Kills an impl that uses an arbitrary or non-deterministic tie-break.
  3. Single-class input → that single class returned.
     Kills an impl that requires ≥2 classes to produce a result.
  4. Empty input → ``None`` (no raises).
     Kills an impl that raises on empty input or returns an empty string.
  5. All same class → that class returned (degenerate case with 1 class).
     Kills an impl that returns ``None`` when all findings share one class.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    most_frequent_problem_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_clear_winner_returned() -> None:
    """The class with the most findings is returned.

    PRIMARY DISCRIMINATOR: kills an impl that returns the first-seen class
    regardless of count (e.g., always returning the first element's class).
    """
    # "beta" has 4 findings (most), "alpha" has 2, "gamma" has 1
    problems = (
        [_p("beta", i) for i in range(4)] + [_p("alpha", i) for i in range(2)] + [_p("gamma")]
    )

    result = most_frequent_problem_class(problems)

    assert result == "beta", f"'beta' has the most findings; got {result!r}"


def test_tie_broken_alphabetically() -> None:
    """Tied classes (equal count) → alphabetically first class returned.

    Kills an impl that uses a non-deterministic or reverse-alphabetical
    tie-break, which would produce different results on equal-count classes.
    """
    # "beta" and "alpha" both have 3 findings; "alpha" < "beta" alphabetically
    problems = [_p("beta", i) for i in range(3)] + [_p("alpha", i) for i in range(3)]

    result = most_frequent_problem_class(problems)

    assert result == "alpha", (
        f"Tie between 'alpha' and 'beta': alphabetical order must pick 'alpha'; got {result!r}"
    )


def test_single_class_returns_that_class() -> None:
    """Single-class input → that class returned.

    Kills an impl that requires ≥2 distinct classes to compute a winner.
    """
    problems = [_p("nesting_outlier", i) for i in range(5)]

    result = most_frequent_problem_class(problems)

    assert result == "nesting_outlier", f"Single class must be returned; got {result!r}"


def test_empty_input_returns_none() -> None:
    """Empty problem list → None (no raises, no empty string).

    Kills an impl that raises ValueError or returns '' on empty input.
    """
    result = most_frequent_problem_class([])

    assert result is None, f"Empty input must return None; got {result!r}"


def test_all_same_class_returns_that_class() -> None:
    """All findings share one class → that class returned (not None).

    Kills an impl that conflates 'only one distinct class' with 'no winner'.
    """
    problems = [_p("compound_smell", i) for i in range(7)]

    result = most_frequent_problem_class(problems)

    assert result == "compound_smell", (
        f"All-same-class input must return that class; got {result!r}"
    )
