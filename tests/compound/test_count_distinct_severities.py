"""Item 369: count_distinct_severities() — number of distinct severities present (2026-06-08).

``count_distinct_severities(problems) -> int``:
Returns the integer count of distinct severity strings in the problem list.
Unlabelled (empty-string severity '') counts as one distinct value if present.
Empty input → 0.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts DISTINCT severities, not total labelled problems.
     Kills impl returning count_problems_with_severity.
  2. Unlabelled '' counts as one distinct value when present.
     Kills impl filtering out unlabelled before counting.
  3. Repeated severity values counted only once.
     Kills impl counting occurrences instead of unique values.
  4. Empty input returns 0.
     Kills impl raising on empty.
  5. All-unlabelled list returns 1 (one distinct severity: '').
     Kills impl returning 0 for all-unlabelled.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    count_distinct_severities,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_counts_distinct_not_total_labelled() -> None:
    """Counts distinct severity values, not total labelled problems.

    PRIMARY DISCRIMINATOR: kills impl returning count_problems_with_severity.
    3 problems all HIGH → 1 distinct severity, not 3.
    """
    problems = [_p("a", "f:0", "HIGH"), _p("b", "f:1", "HIGH"), _p("c", "f:2", "HIGH")]
    result = count_distinct_severities(problems)
    assert result == 1, "All HIGH → 1 distinct; got " + repr(result)


def test_unlabelled_counts_as_one_distinct() -> None:
    """Empty-string severity '' counts as one distinct value.

    Kills impl filtering out unlabelled before counting.
    HIGH + LOW + '' → 3 distinct severities.
    """
    problems = [
        _p("a", "f:0", "HIGH"),
        _p("b", "f:1", "LOW"),
        _p("c", "f:2"),  # severity=''
    ]
    result = count_distinct_severities(problems)
    assert result == 3, "HIGH, LOW, '' = 3 distinct; got " + repr(result)


def test_repeated_values_counted_once() -> None:
    """Repeated severities counted only once.

    Kills impl counting occurrences instead of unique values.
    CRITICAL×3, HIGH×2, MEDIUM×1 → 3 distinct.
    """
    problems = (
        [_p("c", f"f:{i}", "CRITICAL") for i in range(3)]
        + [_p("c", f"f:{i + 3}", "HIGH") for i in range(2)]
        + [_p("c", "f:5", "MEDIUM")]
    )
    result = count_distinct_severities(problems)
    assert result == 3, "3 distinct severities; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0 without raising."""
    assert count_distinct_severities([]) == 0


def test_all_unlabelled_returns_one() -> None:
    """All problems unlabelled → 1 distinct severity (the '' value).

    Kills impl returning 0 for all-unlabelled.
    """
    problems = [_p("a", "f:0"), _p("b", "f:1"), _p("c", "f:2")]
    result = count_distinct_severities(problems)
    assert result == 1, "All '' → 1 distinct; got " + repr(result)
