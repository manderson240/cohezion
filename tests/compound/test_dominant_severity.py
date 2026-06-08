"""Item 249: dominant_severity() — most common severity level (2026-06-08).

``dominant_severity(problems: list[Problem]) -> str | None``:
Returns the non-empty severity string with the highest problem count.
Tie-break: lexicographically smallest string wins.
Returns ``None`` when no problem has a non-empty severity.
Empty *problems* → ``None``.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns the severity with the HIGHEST count, not the
     first non-empty severity seen in input order.
     Kills impl that returns the first non-empty severity (i.e. ignores counts).
  2. Tie-break is lexicographically smallest string.
     Kills impl that returns an arbitrary or last-seen tied severity.
  3. Returns None when no problem has a non-empty severity.
     Kills impl that returns "" or raises on unlabelled-only scans.
  4. Empty input → None.
     Kills impl that raises or returns a non-None default.
  5. Return type is str | None (never a list or dict).
     Kills impl that returns all tied severities as a list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    dominant_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_highest_count_severity_returned() -> None:
    """Returns the severity with the highest count, not the first seen.

    PRIMARY DISCRIMINATOR: kills impl that returns the first non-empty
    severity seen in input order.
    Input order: LOW first, then HIGH × 3.  highest count = HIGH.
    """
    problems = [
        _ps("alpha", 0, "LOW"),            # seen first, but count=1
        _ps("alpha", 1, "HIGH"),           # count=3
        _ps("alpha", 2, "HIGH"),
        _ps("beta",  0, "HIGH"),
    ]
    result = dominant_severity(problems)
    assert result == "HIGH", (
        "HIGH has count=3 > LOW count=1; must return 'HIGH'; got " + repr(result)
    )


def test_tie_break_lexicographically_smallest() -> None:
    """On a tie, the lexicographically smallest severity is returned.

    Kills impl that returns an arbitrary or last-seen tied severity.
    HIGH and LOW each have count=2.  'HIGH' < 'LOW' lexicographically.
    """
    problems = [
        _ps("alpha", 0, "HIGH"), _ps("alpha", 1, "HIGH"),
        _ps("beta",  0, "LOW"),  _ps("beta",  1, "LOW"),
    ]
    result = dominant_severity(problems)
    assert result == "HIGH", (
        "Tied HIGH and LOW → lex-smallest 'HIGH' wins; got " + repr(result)
    )


def test_no_labelled_problems_returns_none() -> None:
    """Returns None when no problem has a non-empty severity.

    Kills impl that returns "" or raises.
    """
    problems = [
        Problem(problem_class="alpha", finding_id="alpha:0"),  # severity=""
        Problem(problem_class="beta",  finding_id="beta:0"),
    ]
    result = dominant_severity(problems)
    assert result is None, (
        "No labelled problems → None; got " + repr(result)
    )


def test_empty_input_returns_none() -> None:
    """Empty problems → None.

    Kills impl that raises or returns a non-None default.
    """
    result = dominant_severity([])
    assert result is None, "Empty input → None; got " + repr(result)


def test_return_type_is_str_or_none() -> None:
    """Return type is str | None, not a list or dict.

    Kills impl that returns all tied severities as a list.
    """
    result = dominant_severity([_ps("alpha", 0, "CRITICAL")])
    assert isinstance(result, str), "Must return str when present; got " + repr(type(result))
    assert result == "CRITICAL"
