"""Item 222: most_critical_class() — class with highest violation ratio (2026-06-08).

``most_critical_class(problems: list[Problem], thresholds: dict[str, int])``
-> ``str | None``:
Returns the class name with the highest ``count / threshold`` ratio from
``class_violation_ratio``.  Tie -> first occurrence in problems wins (or first
key in thresholds if no class appears in problems).  Zero-threshold classes
excluded.  All zero-threshold or empty -> ``None``.  Pure; no I/O.

Ranks classes by RELATIVE pressure, not absolute count.  A class with 10/10
(ratio=1.0) is more critical than one with 8/100 (ratio=0.08)::

    cls = most_critical_class(findings, limits)  # most-pressured category

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns class NAME, not the ratio float.
     Kills an impl that returns the ratio value instead of the class string.
  2. Relative pressure wins over absolute count.
     Kills an impl that delegates to most_common_class (raw count) instead
     of ranking by ratio.
  3. Tie broken by first occurrence in problems, not alphabetically.
     Kills an impl that uses alphabetical tie-breaking.
  4. Zero-threshold class excluded; returns None when all thresholds are zero.
     Kills an impl that triggers ZeroDivisionError or includes zero-threshold.
  5. Empty thresholds -> None; empty problems with positive thresholds -> lowest ratio
     classes all have ratio 0, tie broken by first thresholds key order.
     (Concretely: empty problems -> the first thresholds key if all have equal 0 ratio.)
     Actually simpler: empty problems -> all ratios are 0.0, first in thresholds wins.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    most_critical_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_class_name_not_ratio() -> None:
    """Returns class NAME (str), not the ratio float.

    PRIMARY DISCRIMINATOR: kills an impl that returns the float ratio.
    alpha: 4/5 = 0.8; beta: 3/4 = 0.75 -> most critical is "alpha".
    """
    problems = [_p("alpha", i) for i in range(4)] + [_p("beta", i) for i in range(3)]
    thresholds = {"alpha": 5, "beta": 4}

    result = most_critical_class(problems, thresholds)

    assert result == "alpha", "Must return class name string 'alpha'; got " + repr(result)
    assert isinstance(result, str), "Return type must be str; got " + repr(type(result))


def test_relative_pressure_beats_absolute_count() -> None:
    """Class with highest ratio wins even if its absolute count is lower.

    Kills an impl that delegates to most_common_class (counts only).
    alpha: 9 findings, threshold=100 -> ratio=0.09
    beta:  2 findings, threshold=3   -> ratio=0.67 (more critical despite fewer findings)
    """
    problems = [_p("alpha", i) for i in range(9)] + [_p("beta", i) for i in range(2)]
    thresholds = {"alpha": 100, "beta": 3}

    result = most_critical_class(problems, thresholds)

    assert result == "beta", "beta ratio=0.67 is more critical than alpha ratio=0.09; got " + repr(
        result
    )


def test_tie_broken_by_first_occurrence_in_problems() -> None:
    """Equal ratios resolved by first-seen order in the input list.

    Kills an impl that uses alphabetical tie-breaking.
    beta seen first, both have ratio=1.0 -> "beta" wins.
    """
    # beta appears before alpha in the list; both ratio=3/3=1.0
    problems = [
        _p("beta", 0),
        _p("beta", 1),
        _p("beta", 2),
        _p("alpha", 0),
        _p("alpha", 1),
        _p("alpha", 2),
    ]
    thresholds = {"alpha": 3, "beta": 3}

    result = most_critical_class(problems, thresholds)

    assert result == "beta", "Tie must be broken by first occurrence; got " + repr(result)


def test_zero_threshold_excluded_returns_none_if_all_zero() -> None:
    """Zero-threshold classes are excluded; returns None when all thresholds are 0.

    Kills an impl that triggers ZeroDivisionError or includes zero-threshold.
    """
    problems = [_p("alpha"), _p("beta")]
    thresholds = {"alpha": 0, "beta": 0}

    result = most_critical_class(problems, thresholds)

    assert result is None, "All zero-threshold -> must return None; got " + repr(result)


def test_empty_thresholds_returns_none() -> None:
    """Empty thresholds -> None.

    Kills an impl that raises on empty thresholds.
    """
    problems = [_p("alpha"), _p("beta")]
    result = most_critical_class(problems, {})
    assert result is None, "Empty thresholds must return None; got " + repr(result)
