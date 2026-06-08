"""Item 175: filter_problems() — predicate-based batch filter for Problem lists (2026-06-08).

``filter_problems(problems: list[Problem], predicate: Callable[[Problem], bool])``
→ ``list[Problem]``:
Returns the filtered sublist of *problems* for which *predicate* returns ``True``.
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: ``predicate=lambda p: p.problem_class == "complexity_outlier"``
     applied to a mixed list → only complexity_outlier findings returned.
     Kills an impl that ignores the predicate (returns the full list).
  2. Predicate that matches nothing → [].
     Kills an impl that never returns [].
  3. Predicate that matches all → same list (same elements, same length).
     Kills an impl that always filters at least one element.
  4. Empty input → [].
     Kills an impl that raises on empty input.
  5. Predicate is called on each Problem instance (not on finding_id strings).
     Kills an impl that calls predicate on finding_id strings instead of Problem.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    filter_problems,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_predicate_filters_by_class() -> None:
    """predicate by problem_class → only matching class returned.

    PRIMARY DISCRIMINATOR: kills an impl that ignores the predicate and always
    returns the full input list.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier"), _p("complexity_outlier", 1)]

    result = filter_problems(problems, lambda p: p.problem_class == "complexity_outlier")

    assert len(result) == 2, f"Two complexity_outlier findings expected; got {len(result)}"
    assert all(p.problem_class == "complexity_outlier" for p in result), (
        f"All results must have complexity_outlier class; got {[p.problem_class for p in result]!r}"
    )


def test_matching_nothing_returns_empty() -> None:
    """Predicate that matches nothing → [].

    Kills an impl that never returns [] (e.g., always returns at least one element).
    """
    problems = [_p("alpha"), _p("beta")]

    result = filter_problems(problems, lambda p: p.problem_class == "gamma")

    assert result == [], f"No-match predicate must return []; got {result!r}"


def test_matching_all_returns_full_list() -> None:
    """Predicate that matches every element → same list content.

    Kills an impl that always filters at least one element out.
    """
    problems = [_p("alpha", i) for i in range(3)]

    result = filter_problems(problems, lambda _p: True)

    assert len(result) == len(problems), (
        f"All-match predicate must return all elements; got {len(result)} of {len(problems)}"
    )
    assert {p.finding_id for p in result} == {p.finding_id for p in problems}, (
        f"All-match predicate must include every finding_id; got {result!r}"
    )


def test_empty_input_returns_empty() -> None:
    """Empty problem list → [] (no raises).

    Kills an impl that raises IndexError or similar on empty input.
    """
    result = filter_problems([], lambda p: p.problem_class == "anything")

    assert result == [], f"Empty input must return []; got {result!r}"


def test_predicate_receives_problem_instances() -> None:
    """Predicate is called with Problem instances, not strings or dicts.

    Kills an impl that calls predicate(p.finding_id) instead of predicate(p).
    The predicate accesses p.problem_class (a Problem attribute) — if predicate
    receives a string, it will raise AttributeError.
    """
    received: list[object] = []

    def _capture(p: Problem) -> bool:
        received.append(p)
        return True

    problems = [_p("complexity_outlier")]
    filter_problems(problems, _capture)

    assert len(received) == 1, f"Predicate must be called once; got {len(received)}"
    assert isinstance(received[0], Problem), (
        f"Predicate must receive Problem instance; got {type(received[0])}"
    )
