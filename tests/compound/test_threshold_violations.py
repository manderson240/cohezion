"""Item 203: threshold_violations() — per-class threshold breach report (2026-06-08).

``threshold_violations(problems: list[Problem], thresholds: dict[str, int])``
→ ``dict[str, int]``:
Returns ``{problem_class: excess_count}`` for every monitored class whose
finding count EXCEEDS its threshold.  ``excess_count = count - threshold``.
Class at threshold → absent (0 excess is not a violation).  Unmonitored
classes absent.  Empty *thresholds* → ``{}``.  Pure; no I/O.

Enables human-readable budget reports::

    violations = threshold_violations(findings, {"complexity_outlier": 2})
    # → {"complexity_outlier": 1}  (1 finding over the limit of 2)

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: excess is count − threshold, not raw count.
     Kills an impl that stores the raw finding count instead of the delta.
  2. Class at threshold exactly → absent (count == threshold is fine).
     Kills an impl using >= instead of > (would wrongly flag at-limit).
  3. Unmonitored class → absent.
     Kills an impl that reports every class with count > 0.
  4. Empty thresholds → {}.
     Kills an impl returning counts for all classes on empty thresholds.
  5. Return type is dict[str, int].
     Kills an impl that returns list[str] or a boolean flag.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    threshold_violations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_excess_is_count_minus_threshold() -> None:
    """Violation value is count - threshold, not the raw count.

    PRIMARY DISCRIMINATOR: kills an impl that returns the finding count
    (3) rather than the excess (3 - 2 = 1).
    'alpha' appears 3 times; threshold is 2 → excess = 1.
    """
    problems = [_p("alpha", i) for i in range(3)]
    thresholds = {"alpha": 2}

    result = threshold_violations(problems, thresholds)

    assert result == {"alpha": 1}, f"alpha excess must be 3-2=1; got {result!r}"


def test_class_at_threshold_not_a_violation() -> None:
    """Class whose count equals the threshold → absent from result.

    Kills an impl that uses >= instead of > (which would flag at-limit
    classes as violators with excess=0, which is semantically wrong).
    """
    problems = [_p("beta", i) for i in range(3)]
    thresholds = {"beta": 3}  # count == threshold; no violation

    result = threshold_violations(problems, thresholds)

    assert result == {}, f"count=3 == threshold=3 is not a violation; got {result!r}"


def test_unmonitored_class_absent_from_result() -> None:
    """Class not in thresholds → absent from violations dict.

    Kills an impl that reports all classes with any findings, ignoring
    the thresholds filter.
    """
    problems = [_p("nesting_outlier", i) for i in range(10)]
    thresholds = {"complexity_outlier": 5}  # nesting_outlier not monitored

    result = threshold_violations(problems, thresholds)

    assert result == {}, f"nesting_outlier not monitored; must not appear; got {result!r}"


def test_empty_thresholds_returns_empty_dict() -> None:
    """Empty thresholds → {} regardless of problem list.

    Kills an impl that falls through to counting all classes when no
    thresholds are provided.
    """
    problems = [_p("alpha"), _p("beta")]

    result = threshold_violations(problems, {})

    assert result == {}, f"Empty thresholds must return {{}}; got {result!r}"


def test_return_type_is_dict() -> None:
    """Return value is dict[str, int], not list or bool.

    Kills an impl that returns a list of violating class names or a
    boolean indicating whether any violation exists.
    """
    problems = [_p("complexity_outlier", i) for i in range(5)]
    thresholds = {"complexity_outlier": 2}

    result = threshold_violations(problems, thresholds)

    assert isinstance(result, dict), f"Return type must be dict; got {type(result)!r}"
    assert all(isinstance(v, int) for v in result.values()), "Values must be int (excess counts)"
