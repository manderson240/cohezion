"""Item 214: class_counts_above_threshold() — thresholded count map (2026-06-08).

``class_counts_above_threshold(problems: list[Problem], thresholds: dict[str, int])``
-> ``dict[str, int]``:
Returns ``{problem_class: raw_count}`` for monitored classes whose count
EXCEEDS the threshold.  Values are the RAW count (not count-threshold).
At-threshold classes absent.  Unmonitored absent.  Empty -> ``{}``.
Pure; no I/O.

The raw-count complement to :func:`threshold_violations` (item 203, which
returns excess = count-threshold). Use when callers need the absolute count
rather than the excess::

    counts = class_counts_above_threshold(findings, {"complexity_outlier": 2})
    # -> {"complexity_outlier": 5}  (raw count, not excess=3)

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: values are RAW counts, not excess (count - threshold).
     Kills an impl that returns excess like item 203.
  2. At-threshold class -> absent (not a violation).
     Kills an impl that includes at-threshold classes.
  3. Unmonitored class -> absent.
     Kills an impl that includes all classes from problems.
  4. Empty thresholds -> {} (not raises).
     Kills an impl that raises or returns all classes.
  5. Return type is dict[str, int] with raw count as value.
     Kills an impl that returns a set of class names.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_counts_above_threshold,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_value_is_raw_count_not_excess() -> None:
    """Value in result is the RAW count, not count-threshold.

    PRIMARY DISCRIMINATOR: kills an impl that returns excess (count-threshold)
    as item 203 (threshold_violations) does.
    count=5, threshold=2 -> result["complexity_outlier"] must be 5, not 3.
    """
    problems = [_p("complexity_outlier", i) for i in range(5)]
    thresholds = {"complexity_outlier": 2}

    result = class_counts_above_threshold(problems, thresholds)

    assert "complexity_outlier" in result, "over-threshold class must be in result; got " + repr(
        result
    )
    assert result["complexity_outlier"] == 5, (
        "value must be raw count=5 (not excess=3); got " + repr(result["complexity_outlier"])
    )


def test_at_threshold_class_absent() -> None:
    """Class with count EQUAL to threshold -> absent (not a violation).

    Kills an impl that includes at-threshold classes (using >= instead of >).
    """
    problems = [_p("nesting_outlier", i) for i in range(3)]
    thresholds = {"nesting_outlier": 3}  # count=3, threshold=3 -> at threshold

    result = class_counts_above_threshold(problems, thresholds)

    assert "nesting_outlier" not in result, "at-threshold class must be absent; got " + repr(result)


def test_unmonitored_class_absent() -> None:
    """Class not in thresholds -> absent even if over-count.

    Kills an impl that includes classes from problems regardless of thresholds.
    """
    problems = [_p("long_function", i) for i in range(10)]
    thresholds = {"complexity_outlier": 2}  # long_function not monitored

    result = class_counts_above_threshold(problems, thresholds)

    assert "long_function" not in result, "unmonitored class must be absent; got " + repr(result)


def test_empty_thresholds_returns_empty_dict() -> None:
    """Empty thresholds -> {} (not raises).

    Kills an impl that raises or returns all classes.
    """
    problems = [_p("complexity_outlier", i) for i in range(5)]

    result = class_counts_above_threshold(problems, {})

    assert result == {}, "empty thresholds must return {}; got " + repr(result)


def test_multiple_violating_classes_all_with_raw_counts() -> None:
    """Multiple over-threshold classes -> each maps to its raw count.

    Verifies the raw-count contract across multiple classes simultaneously.
    """
    problems = (
        [_p("alpha", i) for i in range(4)]  # count=4, threshold=1, excess=3
        + [_p("beta", i) for i in range(3)]  # count=3, threshold=2, excess=1
    )
    thresholds = {"alpha": 1, "beta": 2}

    result = class_counts_above_threshold(problems, thresholds)

    assert result == {"alpha": 4, "beta": 3}, "raw counts: alpha=4, beta=3; got " + repr(result)
