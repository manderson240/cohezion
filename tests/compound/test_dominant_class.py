"""Item 421: dominant_class() — class with the highest record count (2026-06-08).

``dominant_class(problems) -> str | None``:
Returns the problem_class with the most records. Ties broken alphabetically
ascending.  Empty -> None.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns str | None (not count or tuple).
     Kills impl returning (class, count) tuple.
  2. Empty -> None (not raise or '').
     Kills impl raising ValueError on empty.
  3. Tie broken alphabetically ascending.
     Kills impl with arbitrary tie-breaking.
  4. Single-class dataset -> that class.
     Validates degenerate case.
  5. Returns class name, not count.
     Kills impl returning the integer count.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    dominant_class,
)


def _p(cls: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_class_name_string() -> None:
    """Returns the class name string, not count or tuple.

    PRIMARY DISCRIMINATOR: kills impl returning (class, count) tuple.
    """
    problems = [_p("big"), _p("big"), _p("small")]
    result = dominant_class(problems)
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "big", "big has most records; got " + repr(result)


def test_empty_returns_none() -> None:
    """Empty input returns None, not raise."""
    result = dominant_class([])
    assert result is None, "Empty -> None; got " + repr(result)


def test_tie_broken_alphabetically_ascending() -> None:
    """Ties broken alphabetically: first class alphabetically wins."""
    # alpha and beta each have 2 records; alpha < beta
    problems = [_p("beta"), _p("beta"), _p("alpha"), _p("alpha")]
    result = dominant_class(problems)
    assert result == "alpha", "Tie: alpha before beta; got " + repr(result)


def test_single_class_returns_that_class() -> None:
    """Single class -> that class name."""
    problems = [_p("only"), _p("only"), _p("only")]
    result = dominant_class(problems)
    assert result == "only", "Single class 'only'; got " + repr(result)


def test_returns_name_not_count() -> None:
    """Returns class name, not the count integer."""
    problems = [_p("cls_a"), _p("cls_a"), _p("cls_a"), _p("cls_b")]
    result = dominant_class(problems)
    assert result == "cls_a", "Should return 'cls_a', not 3; got " + repr(result)
    assert not isinstance(result, int), "Must not return int; got " + repr(type(result))
