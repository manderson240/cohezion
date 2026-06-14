"""Item 178: has_problem_class() — presence check for a problem class (2026-06-08).

``has_problem_class(problems: list[Problem], problem_class: str)`` → ``bool``:
Returns ``True`` if any finding in *problems* has ``problem_class`` equal to the
given string.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: list containing the requested class → ``True``.
     Kills an impl that always returns ``False`` (or always returns ``True``).
  2. List NOT containing the requested class → ``False``.
     Kills an impl that ignores the ``problem_class`` argument and returns ``True``
     for any non-empty list.
  3. Empty list → ``False`` (no raises).
     Kills an impl that raises on empty input or returns ``True`` for empty.
  4. Single-element list that MATCHES → ``True``.
     Kills an impl that requires ≥2 findings to confirm presence.
  5. Single-element list that does NOT match → ``False``.
     Kills an impl that returns ``True`` for any single-element list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    has_problem_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_present_class_returns_true() -> None:
    """List containing the requested class → True.

    PRIMARY DISCRIMINATOR: kills an impl that always returns False, or an impl
    that returns False when the target class is not the first element.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier"), _p("long_function")]

    result = has_problem_class(problems, "nesting_outlier")

    assert result is True, f"'nesting_outlier' is present; expected True but got {result!r}"


def test_absent_class_returns_false() -> None:
    """List NOT containing the requested class → False.

    Kills an impl that ignores the class argument and returns True for any
    non-empty list.
    """
    problems = [_p("complexity_outlier"), _p("long_function")]

    result = has_problem_class(problems, "nesting_outlier")

    assert result is False, f"'nesting_outlier' is absent; expected False but got {result!r}"


def test_empty_list_returns_false() -> None:
    """Empty problem list → False (no raises).

    Kills an impl that raises IndexError / ValueError on empty input or
    returns True for empty input.
    """
    result = has_problem_class([], "complexity_outlier")

    assert result is False, f"Empty list must return False; got {result!r}"


def test_single_element_matching_returns_true() -> None:
    """Single-element list whose class matches → True.

    Kills an impl that requires ≥2 findings before returning True.
    """
    problems = [_p("compound_smell")]

    result = has_problem_class(problems, "compound_smell")

    assert result is True, f"Single matching element must return True; got {result!r}"


def test_single_element_non_matching_returns_false() -> None:
    """Single-element list whose class does NOT match → False.

    Kills an impl that returns True for any single-element list regardless
    of what problem_class the element has.
    """
    problems = [_p("compound_smell")]

    result = has_problem_class(problems, "nesting_outlier")

    assert result is False, f"Single non-matching element must return False; got {result!r}"
