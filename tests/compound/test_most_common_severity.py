"""Item 279: most_common_severity() — globally most frequent severity label (2026-06-08).

``most_common_severity(problems: list[Problem]) -> str | None``:
Returns the severity label with the highest count across all labelled (non-empty
severity) problems. Tie-break: lexicographically ascending severity string.
None when no problem has a non-empty severity or when input is empty.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: excludes severity='' from the frequency count.
     A class with more unlabelled problems than any labelled severity must NOT
     return ""; the most-frequent LABELLED severity wins.
     Kills impl treating "" as just another severity value.
  2. Returns the most frequent labelled severity, not the first seen.
     Kills impl returning the first non-empty severity encountered.
  3. Tie-break: lexicographically ascending severity string.
     Kills impl with wrong tie-break direction.
  4. None when all problems are unlabelled.
     Kills impl returning "" or raising.
  5. Return type is str | None.
     Kills impl returning a count or list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    most_common_severity,
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


def test_excludes_unlabelled_from_count() -> None:
    """severity='' problems are excluded; most frequent LABELLED severity wins.

    PRIMARY DISCRIMINATOR: kills impl that treats '' as a severity value.
    10 unlabelled, 3 HIGH, 1 LOW -> HIGH wins (not '').
    """
    problems = (
        [_p("alpha", i) for i in range(10)]
        + [_ps("beta", i, "HIGH") for i in range(3)]
        + [_ps("gamma", 0, "LOW")]
    )
    result = most_common_severity(problems)
    assert result == "HIGH", (
        "HIGH is most frequent labelled (3 > 1); '' excluded; got " + repr(result)
    )


def test_returns_most_frequent_not_first_seen() -> None:
    """Returns the severity with the highest count, not the first one seen.

    Kills impl returning the first non-empty severity encountered.
    LOW appears first but HIGH appears more often -> HIGH wins.
    """
    problems = [
        _ps("alpha", 0, "LOW"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "HIGH"),
    ]
    result = most_common_severity(problems)
    assert result == "HIGH", "HIGH count=2 > LOW count=1; got " + repr(result)


def test_tie_break_ascending() -> None:
    """Tie-break: lexicographically ascending severity wins (CRITICAL < HIGH).

    Kills impl with wrong tie-break direction.
    HIGH x2, CRITICAL x2 -> CRITICAL wins (alphabetically smaller).
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "CRITICAL"),
        _ps("alpha", 3, "CRITICAL"),
    ]
    result = most_common_severity(problems)
    assert result == "CRITICAL", (
        "CRITICAL < HIGH alphabetically -> wins on tie; got " + repr(result)
    )


def test_none_when_all_unlabelled() -> None:
    """None when all problems have severity=''.

    Kills impl returning '' or raising.
    """
    problems = [_p("alpha", i) for i in range(5)]
    result = most_common_severity(problems)
    assert result is None, "All unlabelled -> None; got " + repr(result)


def test_return_type_str_or_none() -> None:
    """Return type is str | None, not int or list.

    Kills impl returning a count.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = most_common_severity(problems)
    assert isinstance(result, str), "With labelled -> str; got " + repr(type(result))
    none_result = most_common_severity([])
    assert none_result is None, "Empty -> None; got " + repr(none_result)
