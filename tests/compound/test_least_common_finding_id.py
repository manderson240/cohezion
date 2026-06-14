"""Item 365: least_common_finding_id() — rarest finding_id by count (2026-06-08).

``least_common_finding_id(problems) -> str | None``:
Returns the finding_id string with the lowest record count in problems.
Ties broken by ascending finding_id.  None if empty input.  Pure; no I/O.
Complement of most_common_finding_id.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns the LEAST frequent finding_id, not most frequent.
     Kills impl returning most_common_finding_id.
  2. Tie-break by ascending finding_id.
     Kills impl with arbitrary or descending tie-break.
  3. Returns a STRING, not a Problem object.
     Kills impl returning the Problem record.
  4. Empty input returns None.
     Kills impl raising on empty.
  5. Single-occurrence finding_ids all tie at count=1 — ascending name wins.
     Kills impl ignoring tie-break when all counts are equal.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    least_common_finding_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_least_not_most_frequent() -> None:
    """Returns the LEAST frequent finding_id.

    PRIMARY DISCRIMINATOR: kills impl returning most_common_finding_id.
    alpha appears 3x, beta 1x → least is 'beta'.
    """
    problems = [_p("c", "alpha"), _p("c", "alpha"), _p("c", "alpha"), _p("c", "beta")]
    result = least_common_finding_id(problems)
    assert result == "beta", "Least frequent is 'beta'; got " + repr(result)


def test_tie_break_ascending_finding_id() -> None:
    """Ties broken by ascending finding_id.

    Kills impl with arbitrary or descending tie-break.
    alpha=1, beta=1 → 'alpha' wins (ascending).
    """
    problems = [_p("c", "beta"), _p("c", "alpha")]
    result = least_common_finding_id(problems)
    assert result == "alpha", "Tie → ascending name; got " + repr(result)


def test_returns_string_not_problem() -> None:
    """Returns a str, not a Problem object.

    Kills impl returning the Problem record.
    """
    problems = [_p("c", "fid:0"), _p("c", "fid:0"), _p("c", "fid:1")]
    result = least_common_finding_id(problems)
    assert isinstance(result, str), "Must be str; got " + repr(type(result))
    assert result == "fid:1", "Least frequent is fid:1; got " + repr(result)


def test_empty_returns_none() -> None:
    """Empty input returns None without raising."""
    assert least_common_finding_id([]) is None


def test_all_single_occurrence_ascending_name_wins() -> None:
    """All finding_ids appear once; ascending name is the tiebreaker.

    Kills impl ignoring tie-break when all counts are equal.
    """
    problems = [_p("c", "zzz"), _p("c", "aaa"), _p("c", "mmm")]
    result = least_common_finding_id(problems)
    assert result == "aaa", "All count=1 → ascending name; got " + repr(result)
