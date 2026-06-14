"""Item 205: violation_summary() — total excess across all violating classes (2026-06-08).

``violation_summary(problems: list[Problem], thresholds: dict[str, int])``
-> ``int``:
Returns ``sum(threshold_violations(problems, thresholds).values())`` — the
total excess findings across all monitored classes that exceed their limit.
Zero when no class violates its threshold.  Empty *thresholds* -> ``0``.
Pure; no I/O.

Enables a single boolean health gate without unpacking the violations dict::

    if violation_summary(findings, limits) > 0:
        trigger_alert()

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: sum of all per-class excesses (not count of violating classes).
     Kills an impl that returns len(threshold_violations()) instead of sum.
  2. No violations -> 0, not None.
     Kills an impl that returns None when there are no violating classes.
  3. Empty thresholds -> 0.
     Kills an impl that returns None or raises on empty thresholds.
  4. Return type is int.
     Kills an impl that returns a float or dict.
  5. Single class with large excess -> that excess value (correct single-class sum).
     Kills an impl that caps at 1 per class.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    violation_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sum_of_excesses_not_count_of_violators() -> None:
    """Returns sum of all excess counts, not the number of violating classes.

    PRIMARY DISCRIMINATOR: kills an impl that returns len(violations).
    Two violating classes: alpha (excess=2), beta (excess=1) -> sum=3, not count=2.
    """
    # alpha: 3 findings, threshold=1 -> excess=2
    # beta:  2 findings, threshold=1 -> excess=1
    problems = [_p("alpha", i) for i in range(3)] + [_p("beta", i) for i in range(2)]
    thresholds = {"alpha": 1, "beta": 1}

    result = violation_summary(problems, thresholds)

    assert result == 3, "sum of excesses must be 2+1=3; got " + repr(result)


def test_no_violations_returns_zero() -> None:
    """All classes within threshold -> 0, not None.

    Kills an impl that returns None when there are no violating classes.
    """
    problems = [_p("alpha")]
    thresholds = {"alpha": 5}  # count=1 <= threshold=5

    result = violation_summary(problems, thresholds)

    assert result == 0, f"No violations must return 0; got {result!r}"


def test_empty_thresholds_returns_zero() -> None:
    """Empty thresholds -> 0.

    Kills an impl that raises or returns None when thresholds is empty.
    """
    problems = [_p("alpha"), _p("beta")]

    result = violation_summary(problems, {})

    assert result == 0, f"Empty thresholds must return 0; got {result!r}"


def test_return_type_is_int() -> None:
    """Return value is int, not float or dict.

    Kills an impl that returns float(sum) or a violations dict.
    """
    problems = [_p("complexity_outlier", i) for i in range(4)]
    thresholds = {"complexity_outlier": 2}

    result = violation_summary(problems, thresholds)

    assert isinstance(result, int), f"Return type must be int; got {type(result)!r}"
    assert result == 2  # count=4, threshold=2, excess=2


def test_single_class_large_excess() -> None:
    """Single violating class with excess > 1 -> that full excess.

    Kills an impl that caps per-class contribution at 1 (treating it as
    a count of violators rather than the actual excess magnitude).
    """
    problems = [_p("nesting_outlier", i) for i in range(10)]
    thresholds = {"nesting_outlier": 3}  # excess = 10 - 3 = 7

    result = violation_summary(problems, thresholds)

    assert result == 7, f"Single class excess must be 10-3=7; got {result!r}"
