"""Item 232: total_violation_depth() — aggregate excess across all violations (2026-06-08).

``total_violation_depth(problems: list[Problem], thresholds: dict[str, int])``
-> ``int``:
Returns the sum of all per-class excesses: ``sum(violation_depth(...).values())``.
Zero when no violations or empty thresholds.  Pure; no I/O.

Enables a single integer "how overloaded is this codebase?" metric:
  violations_count  = number of violating classes  (is any class over?)
  violation_summary = same as total_violation_depth (sum of excesses)
  total_violation_depth = direct delegation to violation_depth sum

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns sum of ALL excesses, NOT the count of violating classes.
     Kills an impl that returns violations_count (1 for one class, 2 for two classes).
  2. Returns 0 when no class is violating.
     Kills an impl that returns a count of problems.
  3. Empty thresholds -> 0.
     Kills an impl that raises or returns None.
  4. Return type is int, not float or dict.
     Kills an impl that returns violation_depth directly.
  5. Multiple violations: depths sum correctly.
     Kills an impl that returns max depth instead of sum.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    total_violation_depth,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_sum_of_depths_not_violation_count() -> None:
    """Returns sum of per-class excesses, not the count of violating classes.

    PRIMARY DISCRIMINATOR: kills an impl that returns violations_count.
    alpha: count=7, threshold=3  -> depth=4
    beta:  count=5, threshold=2  -> depth=3
    sum = 7, NOT 2 (the number of violating classes).
    """
    problems = [_p("alpha", i) for i in range(7)] + [_p("beta", i) for i in range(5)]
    thresholds = {"alpha": 3, "beta": 2}

    result = total_violation_depth(problems, thresholds)

    assert result == 7, "alpha_depth=4 + beta_depth=3 = 7; got " + repr(result)


def test_returns_zero_when_no_violations() -> None:
    """Returns 0 when all classes are within threshold.

    Kills an impl that returns a count of all problems.
    """
    problems = [_p("alpha", i) for i in range(2)] + [_p("beta")]
    thresholds = {"alpha": 5, "beta": 3}

    result = total_violation_depth(problems, thresholds)

    assert result == 0, "No violations -> must return 0; got " + repr(result)


def test_empty_thresholds_returns_zero() -> None:
    """Empty thresholds -> 0.

    Kills an impl that raises or returns None.
    """
    problems = [_p("alpha", i) for i in range(10)]
    result = total_violation_depth(problems, {})
    assert result == 0, "Empty thresholds must return 0; got " + repr(result)


def test_return_type_is_int() -> None:
    """Return type is int, not float or dict.

    Kills an impl that returns violation_depth(...) directly.
    """
    problems = [_p("alpha", i) for i in range(5)]
    thresholds = {"alpha": 2}

    result = total_violation_depth(problems, thresholds)

    assert isinstance(result, int), "Return type must be int; got " + repr(type(result))
    assert result == 3


def test_multiple_violations_depths_sum() -> None:
    """Multiple violations: each depth added, not the maximum taken.

    Kills an impl that returns max depth instead of sum.
    alpha: count=5, threshold=3 -> depth=2
    beta:  count=8, threshold=4 -> depth=4
    gamma: count=3, threshold=3 -> at-threshold (depth=0, absent)
    sum = 2 + 4 = 6, NOT max(2, 4) = 4.
    """
    problems = (
        [_p("alpha", i) for i in range(5)]
        + [_p("beta", i) for i in range(8)]
        + [_p("gamma", i) for i in range(3)]
    )
    thresholds = {"alpha": 3, "beta": 4, "gamma": 3}

    result = total_violation_depth(problems, thresholds)

    assert result == 6, "alpha_depth=2 + beta_depth=4 = 6; got " + repr(result)
