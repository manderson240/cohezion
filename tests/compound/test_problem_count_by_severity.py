"""Item 327: problem_count_by_severity() — total Problem record count per severity (2026-06-08).

``problem_count_by_severity(problems) -> dict[str, int]``:
Returns {severity_label: total_record_count} across all classes.
Unlabelled problems (severity='') excluded.  Empty -> {}.  Pure; no I/O.

Inverse of class_count_by_severity: where that counts DISTINCT CLASSES per severity,
this counts total RECORDS per severity.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: count = total RECORDS not distinct classes.
     Kills impl counting distinct classes (class_count_by_severity semantics).
  2. Records from multiple classes aggregate into the same severity bucket.
     Kills impl counting per-class separately (would give max 1 per class).
  3. Unlabelled problems excluded; '' not a key.
     Kills impl including empty-string severity.
  4. Empty -> {}.
     Kills impl crashing on empty input.
  5. Single labelled record -> {severity: 1}.
     Kills impl off-by-one returning 0 or empty.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problem_count_by_severity,
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


def test_count_is_total_records_not_distinct_classes() -> None:
    """count = total Problem records at severity (NOT distinct classes).

    PRIMARY DISCRIMINATOR: kills impl counting distinct classes.
    alpha: 5 HIGH. beta: 3 HIGH. Total HIGH = 8 (not 2 classes).
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(5)] + [
        _ps("beta", i, "HIGH") for i in range(3)
    ]
    result = problem_count_by_severity(problems)
    assert result.get("HIGH") == 8, "HIGH: 5 alpha + 3 beta = 8 total records; got " + repr(
        result.get("HIGH")
    )


def test_records_from_multiple_classes_aggregate() -> None:
    """Records across classes sum into the same bucket.

    Kills impl counting per-class and returning separate values.
    alpha HIGH=2, beta HIGH=3 -> HIGH=5 in result.
    alpha LOW=1 -> LOW=1.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "LOW"),
        _ps("beta", 0, "HIGH"),
        _ps("beta", 1, "HIGH"),
        _ps("beta", 2, "HIGH"),
    ]
    result = problem_count_by_severity(problems)
    assert result.get("HIGH") == 5, "alpha(2)+beta(3) HIGH=5; got " + repr(result.get("HIGH"))
    assert result.get("LOW") == 1, "alpha(1) LOW=1; got " + repr(result.get("LOW"))


def test_unlabelled_problems_excluded() -> None:
    """Unlabelled problems excluded; '' must not be a key in result.

    Kills impl including empty-string severity as a key.
    """
    problems = [_p("alpha", 0), _p("alpha", 1), _ps("alpha", 2, "HIGH")]
    result = problem_count_by_severity(problems)
    assert "" not in result, "'' must not be in result; got " + repr(result)
    assert result.get("HIGH") == 1, "1 HIGH; got " + repr(result)


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {} without raising."""
    result = problem_count_by_severity([])
    assert result == {}, "empty -> {}; got " + repr(result)


def test_single_labelled_record_gives_count_one() -> None:
    """Single labelled record -> {severity: 1}.

    Kills impl off-by-one returning 0 or KeyError.
    """
    problems = [_ps("alpha", 0, "CRITICAL")]
    result = problem_count_by_severity(problems)
    assert result == {"CRITICAL": 1}, "Single record -> {CRITICAL: 1}; got " + repr(result)
