"""Item 179: has_any_problem_class() — multi-class CI gate predicate (2026-06-08).

``has_any_problem_class(problems: list[Problem], classes: frozenset[str])`` → ``bool``:
Returns ``True`` if any finding belongs to at least one class in *classes*.
Empty *classes* → ``False``.  Empty *problems* → ``False``.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: mixed list with one matching class → ``True``.
     Kills an impl that requires ALL classes to match (AND logic instead of OR).
  2. No finding matches any class → ``False``.
     Kills an impl that ignores *classes* and returns ``True`` for any non-empty list.
  3. Empty *classes* set → ``False``.
     Kills an impl that returns ``True`` for empty *classes* (treats empty as "match all").
  4. Empty *problems* list → ``False`` (no raises).
     Kills an impl that raises on empty input.
  5. All findings match → ``True`` (degenerate case confirming OR not AND logic).
     Kills an impl that demands every class in *classes* appear at least once.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    has_any_problem_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_one_class_matches_returns_true() -> None:
    """Mixed list where exactly one class from *classes* appears → True.

    PRIMARY DISCRIMINATOR: kills an impl that uses AND logic (requires every
    class in *classes* to appear at least once) instead of OR logic (any match).
    'complexity_outlier' is in both the problem list and *classes*;
    'nesting_outlier' is in *classes* but NOT in the problem list.
    """
    problems = [_p("complexity_outlier"), _p("long_function")]

    result = has_any_problem_class(problems, frozenset({"complexity_outlier", "nesting_outlier"}))

    assert result is True, (
        f"'complexity_outlier' is in classes and in problems; expected True but got {result!r}"
    )


def test_no_matching_class_returns_false() -> None:
    """No finding matches any class in *classes* → False.

    Kills an impl that ignores *classes* and returns True for any non-empty list.
    """
    problems = [_p("long_function"), _p("compound_smell")]

    result = has_any_problem_class(problems, frozenset({"complexity_outlier", "nesting_outlier"}))

    assert result is False, f"No match in classes; expected False but got {result!r}"


def test_empty_classes_returns_false() -> None:
    """Empty *classes* → False (nothing to match against).

    Kills an impl that treats empty *classes* as "match everything" (returns True
    for any non-empty problems list when classes is empty).
    """
    problems = [_p("complexity_outlier")]

    result = has_any_problem_class(problems, frozenset())

    assert result is False, f"Empty classes must return False; got {result!r}"


def test_empty_problems_returns_false() -> None:
    """Empty *problems* → False (no raises).

    Kills an impl that raises IndexError / ValueError on empty input.
    """
    result = has_any_problem_class([], frozenset({"complexity_outlier"}))

    assert result is False, f"Empty problems must return False; got {result!r}"


def test_all_findings_match_returns_true() -> None:
    """All findings share a class that is in *classes* → True.

    Kills an impl that demands every class in *classes* appear at least once
    (AND logic): only 'complexity_outlier' appears, 'nesting_outlier' does
    not — an AND impl would incorrectly return False.
    """
    problems = [_p("complexity_outlier", i) for i in range(3)]

    result = has_any_problem_class(problems, frozenset({"complexity_outlier", "nesting_outlier"}))

    assert result is True, (
        f"All findings match one class from classes; expected True but got {result!r}"
    )
