"""Item 273: top_class_by_problem_count() — class with the most problems (2026-06-08).

``top_class_by_problem_count(problems: list[Problem]) -> str | None``:
Returns the class name with the largest total problem count (all severities
included); tie-break: class name ascending; None when input is empty.
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns class with the MOST problems, not fewest or random.
     Kills impl returning the first class seen or the alphabetically first
     regardless of count.
  2. Tie-break is ascending class name (alphabetically smallest wins on tie).
     Kills impl with tie-break descending or by insertion order.
  3. Returns None on empty input (not "" or KeyError).
     Kills impl that raises or returns empty string.
  4. Counts ALL problems in a class (regardless of severity).
     Kills impl that only counts labelled problems (severity != "").
  5. Return type is str (or None).
     Kills impl returning a tuple, int, or list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_class_by_problem_count,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_class_with_most_problems() -> None:
    """Returns the class that has the most problems.

    PRIMARY DISCRIMINATOR: kills impl returning first/alphabetic class.
    alpha: 1 problem; beta: 3 problems; gamma: 2 problems. beta must win.
    """
    problems = [
        _p("alpha", 0),
        _p("beta", 0),
        _p("beta", 1),
        _p("beta", 2),
        _p("gamma", 0),
        _p("gamma", 1),
    ]
    result = top_class_by_problem_count(problems)
    assert result == "beta", "beta has 3 problems (most); got " + repr(result)


def test_tiebreak_ascending_class_name() -> None:
    """Tie-break is ascending class name (alphabetically smallest wins).

    Kills impl with descending tie-break or insertion-order tie-break.
    alpha and bravo both have 2 problems; alpha < bravo lexicographically.
    """
    problems = [
        _p("bravo", 0),
        _p("bravo", 1),
        _p("alpha", 0),
        _p("alpha", 1),
    ]
    result = top_class_by_problem_count(problems)
    assert result == "alpha", "alpha and bravo tied at 2; tie-break ascending → alpha; got " + repr(
        result
    )


def test_returns_none_on_empty_input() -> None:
    """Returns None (not '') on empty input.

    Kills impl that raises or returns an empty string.
    """
    result = top_class_by_problem_count([])
    assert result is None, "Empty input must return None; got " + repr(result)


def test_counts_unlabelled_problems_too() -> None:
    """Counts ALL problems including those with severity=''.

    Kills impl that only counts labelled problems.
    alpha: 2 labelled; beta: 1 labelled + 2 unlabelled = 3 total.
    beta must win because raw count includes unlabelled.
    """
    problems = [
        _p("alpha", 0, "HIGH"),
        _p("alpha", 1, "LOW"),
        _p("beta", 0, "HIGH"),
        _p("beta", 1),
        _p("beta", 2),
    ]
    result = top_class_by_problem_count(problems)
    assert result == "beta", (
        "beta has 3 total (2 unlabelled); must count ALL problems; got " + repr(result)
    )


def test_return_type_is_str_or_none() -> None:
    """Return type is str (non-empty) or None.

    Kills impl returning tuple, int, or list.
    """
    single = [_p("alpha", 0)]
    result = top_class_by_problem_count(single)
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "alpha", "Single class must return that class name"
