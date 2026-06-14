"""Item 422: dominant_finding_id() — finding_id with the highest total record count (2026-06-08).

``dominant_finding_id(problems) -> str | None``:
Returns the finding_id with the most total records. Ties broken alphabetically
ascending.  Empty -> None.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on finding_id (not problem_class).
     Kills impl reusing dominant_class (wrong field).
  2. Empty -> None (not raise or '').
     Kills impl raising ValueError on empty.
  3. Tie broken alphabetically ascending by finding_id.
     Kills impl with arbitrary tie-breaking.
  4. Returns str | None, not count or tuple.
     Kills impl returning (fid, count) tuple.
  5. Cross-class repetition counts toward total.
     Kills impl requiring same class for fid count.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    dominant_finding_id,
)


def _p(fid: str, cls: str = "cls") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_keyed_on_finding_id_not_class() -> None:
    """Returns the finding_id with most records (not class name).

    PRIMARY DISCRIMINATOR: kills impl reusing dominant_class.
    """
    problems = [_p("fid_a"), _p("fid_a"), _p("fid_b")]
    result = dominant_finding_id(problems)
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "fid_a", "fid_a has 2 records; got " + repr(result)


def test_empty_returns_none() -> None:
    """Empty input returns None, not raise."""
    result = dominant_finding_id([])
    assert result is None, "Empty -> None; got " + repr(result)


def test_tie_broken_alphabetically_ascending() -> None:
    """Ties broken alphabetically: lexicographically smallest fid wins."""
    problems = [_p("beta_fid"), _p("beta_fid"), _p("alpha_fid"), _p("alpha_fid")]
    result = dominant_finding_id(problems)
    assert result == "alpha_fid", "Tie: alpha_fid before beta_fid; got " + repr(result)


def test_returns_fid_string_not_count() -> None:
    """Returns fid string, not the count integer or tuple."""
    problems = [_p("solo"), _p("solo"), _p("solo")]
    result = dominant_finding_id(problems)
    assert result == "solo", "Should return 'solo', not 3; got " + repr(result)
    assert not isinstance(result, int), "Must not return int"
    assert not isinstance(result, tuple), "Must not return tuple"


def test_cross_class_records_counted() -> None:
    """fid occurring in multiple classes contributes to its total count."""
    p0 = _p("shared", "classA")
    p1 = _p("shared", "classB")
    p2 = _p("unique", "classA")
    result = dominant_finding_id([p0, p1, p2])
    assert result == "shared", "shared has 2 total records (cross-class); got " + repr(result)
