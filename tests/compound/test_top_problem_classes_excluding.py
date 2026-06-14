"""Item 169: top_problem_classes_excluding() — ranked classes with exclude guard (2026-06-08).

``top_problem_classes_excluding(problems, *, exclude_classes=frozenset(), n=5)`` →
``list[tuple[str, int]]``: extends :func:`top_problem_classes` (item 161) with an
optional exclusion set.  Classes in *exclude_classes* are omitted from the ranking
result.  When *exclude_classes* is empty, the result is identical to
:func:`top_problem_classes`.

Exclusion happens BEFORE ranking, so ``n`` refers to the top-n from the
NON-EXCLUDED classes.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: ``exclude_classes={"noisy_class"}`` applied to a result where
     ``noisy_class`` is the top-ranked class → ``noisy_class`` NOT in the result.
     Kills an impl that ignores ``exclude_classes``.
  2. ``exclude_classes=frozenset()`` → identical to ``top_problem_classes``.
     Kills an impl that always filters (produces wrong result for empty exclude).
  3. ``n=1`` with 3 distinct classes → only the top non-excluded class returned.
     Kills an impl that ignores the ``n`` limit.
  4. Tie-breaking matches ``top_problem_classes`` (descending count, alphabetical).
     Kills an impl that uses a different sort order.
  5. All classes excluded → empty list.
     Kills an impl that raises on a fully-excluded input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_problem_classes,
    top_problem_classes_excluding,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_excluded_class_absent_from_result() -> None:
    """exclude_classes={"noisy"} where 'noisy' is the top class → 'noisy' absent.

    PRIMARY DISCRIMINATOR: kills an impl that ignores exclude_classes entirely
    and returns the same list as top_problem_classes.
    """
    # 'noisy' has 5 occurrences (top), 'alpha' has 2, 'beta' has 1
    problems = (
        [_p("noisy", i) for i in range(5)] + [_p("alpha", i) for i in range(2)] + [_p("beta")]
    )

    result = top_problem_classes_excluding(problems, exclude_classes={"noisy"})

    class_names = [cls for cls, _ in result]
    assert "noisy" not in class_names, f"'noisy' must be excluded from result; got {class_names!r}"
    assert "alpha" in class_names, (
        f"'alpha' must appear in result (not excluded); got {class_names!r}"
    )


def test_empty_exclude_matches_top_problem_classes() -> None:
    """exclude_classes=frozenset() → identical to top_problem_classes.

    Kills an impl that always applies filtering even when exclude_classes is empty.
    """
    problems = [_p("a", i) for i in range(3)] + [_p("b", i) for i in range(2)] + [_p("c")]

    expected = top_problem_classes(problems)
    result = top_problem_classes_excluding(problems, exclude_classes=frozenset())

    assert result == expected, (
        f"Empty exclude_classes must match top_problem_classes; got {result!r} vs {expected!r}"
    )


def test_n_limits_result_to_top_non_excluded() -> None:
    """n=1 with 3 distinct classes → only the single top non-excluded class.

    Kills an impl that ignores the ``n`` parameter (would return all classes).
    Also tests that n counts from the non-excluded pool, not the original.
    """
    # 'excluded' has 10 (would be top), 'alpha' has 3, 'beta' has 2, 'gamma' has 1
    problems = (
        [_p("excluded", i) for i in range(10)]
        + [_p("alpha", i) for i in range(3)]
        + [_p("beta", i) for i in range(2)]
        + [_p("gamma")]
    )

    result = top_problem_classes_excluding(
        problems,
        exclude_classes={"excluded"},
        n=1,
    )

    assert len(result) == 1, f"n=1 must return exactly 1 entry; got {len(result)}"
    assert result[0][0] == "alpha", (
        f"Top non-excluded class is 'alpha' (count=3); got {result[0]!r}"
    )


def test_tiebreaking_is_alphabetical() -> None:
    """Tie (equal counts) → alphabetical order, consistent with top_problem_classes.

    Kills an impl that uses a different sort order for tied classes.
    """
    # 'beta' and 'alpha' both have count=2; alphabetical → alpha first
    problems = [_p("beta", i) for i in range(2)] + [_p("alpha", i) for i in range(2)]

    result = top_problem_classes_excluding(problems, exclude_classes=frozenset())
    names = [cls for cls, _ in result]

    assert names[0] == "alpha", (
        f"Tied classes: alphabetical order expected (alpha before beta); got {names!r}"
    )
    assert names[1] == "beta"


def test_all_classes_excluded_returns_empty() -> None:
    """All classes in exclude_classes → empty list (no raises).

    Kills an impl that raises when every class is excluded (instead of
    returning an empty list gracefully).
    """
    problems = [_p("alpha"), _p("beta")]

    result = top_problem_classes_excluding(
        problems,
        exclude_classes={"alpha", "beta"},
    )

    assert result == [], f"All classes excluded must return []; got {result!r}"
