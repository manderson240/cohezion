"""Item 204: worst_violation() — single largest threshold breach (2026-06-08).

``worst_violation(problems: list[Problem], thresholds: dict[str, int])``
→ ``tuple[str, int] | None``:
Returns ``(problem_class, excess_count)`` for the class with the highest
``excess_count`` (= count − threshold) among all over-threshold classes.
Ties broken by first-occurrence order in *problems* (first-seen class wins).
No violations → ``None``.  Pure; no I/O.

The scalar counterpart to :func:`threshold_violations`; avoids callers
writing ``max(violations.items(), key=lambda kv: kv[1])`` manually::

    if v := worst_violation(findings, limits):
        alert(f"{v[0]} exceeds budget by {v[1]}")

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns class with highest EXCESS (not highest raw count).
     Kills an impl that uses raw count instead of count−threshold.
  2. Tie → first-occurrence class wins (not last, not alphabetical).
     Kills an impl that picks an arbitrary or alphabetical winner on ties.
  3. No violations → None (not raises).
     Kills an impl that raises KeyError or returns a placeholder tuple.
  4. Return is (str, int) tuple; excess value is count−threshold, not count.
     Kills an impl that returns the raw count as the second element.
  5. Empty thresholds → None (no entry can be over any threshold).
     Kills an impl that returns a random class on empty thresholds.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    worst_violation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_class_with_highest_excess_not_raw_count() -> None:
    """Returns the class whose excess (count − threshold) is largest.

    PRIMARY DISCRIMINATOR: kills an impl that uses raw count instead of
    excess.  Here 'complexity_outlier' has count=5, threshold=4 → excess=1.
    'nesting_outlier' has count=3, threshold=1 → excess=2.  The winner must
    be 'nesting_outlier' (higher excess), not 'complexity_outlier' (higher
    raw count).
    """
    problems = [
        _p("complexity_outlier", i)
        for i in range(5)  # count=5, threshold=4, excess=1
    ] + [
        _p("nesting_outlier", i)
        for i in range(3)  # count=3, threshold=1, excess=2
    ]
    thresholds = {"complexity_outlier": 4, "nesting_outlier": 1}

    result = worst_violation(problems, thresholds)

    assert result is not None, "Must return a tuple when violations exist"
    cls, excess = result
    assert cls == "nesting_outlier", (
        "nesting_outlier has excess=2 vs complexity_outlier excess=1; "
        "worst must be nesting_outlier; got " + repr(cls)
    )
    assert excess == 2, "excess must be count−threshold = 3−1 = 2; got " + repr(excess)


def test_tie_broken_by_first_occurrence() -> None:
    """Tie in excess → first-occurrence class wins (not alphabetical).

    Kills an impl that picks alphabetically (would return 'alpha' here,
    not 'zeta' which appears first in the list).
    """
    # 'zeta' appears first; both have excess=1
    problems = [
        _p("zeta", 0),
        _p("zeta", 1),  # count=2, threshold=1, excess=1
        _p("alpha", 0),
        _p("alpha", 1),  # count=2, threshold=1, excess=1
    ]
    thresholds = {"zeta": 1, "alpha": 1}

    result = worst_violation(problems, thresholds)

    assert result is not None
    cls, excess = result
    assert cls == "zeta", (
        "Tie must be broken by first occurrence ('zeta' appears before 'alpha'); got " + repr(cls)
    )
    assert excess == 1


def test_no_violations_returns_none() -> None:
    """No class exceeds its threshold → None (not raises).

    Kills an impl that raises KeyError or returns a dummy tuple.
    """
    problems = [_p("complexity_outlier", i) for i in range(2)]
    thresholds = {"complexity_outlier": 5}  # count=2 ≤ threshold=5

    result = worst_violation(problems, thresholds)

    assert result is None, "No violations must return None; got " + repr(result)


def test_return_tuple_has_excess_not_raw_count() -> None:
    """Second element of the returned tuple is excess, not raw count.

    Kills an impl that returns the raw count (3) instead of excess (1).
    """
    problems = [_p("long_function", i) for i in range(3)]  # count=3
    thresholds = {"long_function": 2}  # excess = 3 − 2 = 1

    result = worst_violation(problems, thresholds)

    assert result is not None
    cls, excess = result
    assert cls == "long_function"
    assert excess == 1, "Second element must be excess (count−threshold = 3−2 = 1); got " + repr(
        excess
    )


def test_empty_thresholds_returns_none() -> None:
    """Empty thresholds → None (nothing can be over-threshold).

    Kills an impl that returns a class from problems on empty thresholds.
    """
    problems = [_p("complexity_outlier", i) for i in range(5)]

    result = worst_violation(problems, {})

    assert result is None, "Empty thresholds must return None; got " + repr(result)
