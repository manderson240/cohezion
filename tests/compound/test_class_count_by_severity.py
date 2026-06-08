"""Item 320: class_count_by_severity() — distinct classes per severity level (2026-06-08).

``class_count_by_severity(problems) -> dict[str, int]``:
Returns {severity: count_of_distinct_classes_with_at_least_one_problem_at_that_severity}.
Unlabelled problems (severity='') excluded.  Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: count = distinct classes, NOT total problems at severity.
     Kills impl counting raw problem occurrences instead of class presence.
  2. Class with multiple problems at same severity counts as 1.
     Kills impl incrementing count once per problem (not per class).
  3. Unlabelled problems excluded entirely.
     Kills impl including '' as a key in the result.
  4. Same class appears under multiple severities independently.
     Kills impl short-circuiting once a class is counted for one severity.
  5. Empty -> {}.
     Kills impl crashing on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_count_by_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_count_is_distinct_classes_not_total_problems() -> None:
    """count = number of DISTINCT classes with >= 1 problem at that severity.

    PRIMARY DISCRIMINATOR: kills impl that counts raw problem occurrences.
    alpha: 5 HIGH problems -> HIGH count = 1, not 5.
    beta:  2 HIGH problems -> HIGH count = 2 total (alpha + beta), not 7.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "HIGH"),
        _ps("alpha", 3, "HIGH"),
        _ps("alpha", 4, "HIGH"),
        _ps("beta", 0, "HIGH"),
        _ps("beta", 1, "HIGH"),
    ]
    result = class_count_by_severity(problems)
    assert result.get("HIGH") == 2, (
        "HIGH: 2 distinct classes (alpha+beta); got " + repr(result.get("HIGH"))
    )


def test_class_counted_once_per_severity_even_with_many_problems() -> None:
    """Class with 5 HIGH problems contributes count=1 to HIGH, not 5.

    Kills impl that increments for each problem occurrence.
    alpha: 5 HIGH -> HIGH count = 1.
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(5)]
    result = class_count_by_severity(problems)
    assert result.get("HIGH") == 1, (
        "alpha (5 HIGH) counts as 1 class; got " + repr(result.get("HIGH"))
    )


def test_unlabelled_problems_excluded() -> None:
    """Unlabelled problems (severity='') are excluded; '' must not be a key.

    Kills impl including empty-string severity as a result key.
    alpha: 2 unlabelled, 1 HIGH -> result = {HIGH: 1} (no '' key).
    """
    problems = [_p("alpha", 0), _p("alpha", 1), _ps("alpha", 2, "HIGH")]
    result = class_count_by_severity(problems)
    assert "" not in result, "'' must not be a key; got " + repr(result)
    assert result.get("HIGH") == 1, "alpha HIGH=1; got " + repr(result)


def test_same_class_counted_independently_per_severity() -> None:
    """A class appears under each severity it has problems for, independently.

    Kills impl that only counts a class once across all severities.
    alpha: 1 HIGH, 1 CRITICAL -> HIGH=1, CRITICAL=1 (both in result).
    beta:  1 HIGH -> HIGH=2 (alpha+beta).
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "CRITICAL"),
        _ps("beta", 0, "HIGH"),
    ]
    result = class_count_by_severity(problems)
    assert result.get("HIGH") == 2, "HIGH: alpha+beta = 2; got " + repr(result.get("HIGH"))
    assert result.get("CRITICAL") == 1, "CRITICAL: alpha only = 1; got " + repr(result.get("CRITICAL"))


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {} without raising.

    Kills impl that crashes on empty list.
    """
    result = class_count_by_severity([])
    assert result == {}, "empty -> {}; got " + repr(result)
