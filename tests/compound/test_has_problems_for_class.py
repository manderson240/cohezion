"""Item 398: has_problems_for_class() — boolean presence check for a class (2026-06-08).

``has_problems_for_class(problems, target_class) -> bool``:
Returns True if at least one Problem record has problem_class == target_class.
Returns False when the class is absent or problems is empty.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns a BOOL, not an integer count.
     Kills impl returning problem_count_for_class result (2 vs True differ on type).
  2. Returns False (not 0, not None) when class is absent.
     Kills impl returning the count (0 is falsy but not False).
  3. Returns True when at least one matching record exists.
     Kills impl requiring >1 record to return True.
  4. Empty problems -> False.
     Kills impl raising on empty.
  5. Returns False when problems exist but no record matches.
     Kills impl returning True for any non-empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    has_problems_for_class,
)


def _p(cls: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_bool_not_int() -> None:
    """Returns a bool, not an integer count.

    PRIMARY DISCRIMINATOR: kills impl returning problem_count_for_class.
    """
    problems = [_p("alpha"), _p("beta")]
    result = has_problems_for_class(problems, "alpha")
    assert type(result) is bool, "Must return bool; got " + repr(type(result))
    assert result is True, "alpha present -> True; got " + repr(result)


def test_false_is_bool_not_zero_when_absent() -> None:
    """Returns False (bool), not 0 (int) when class is absent.

    Kills impl returning the count (0 is falsy but type is int, not bool).
    """
    result = has_problems_for_class([_p("alpha")], "missing")
    assert type(result) is bool, "Must return bool not int; got " + repr(type(result))
    assert result is False


def test_true_on_single_matching_record() -> None:
    """Returns True when exactly one record matches.

    Kills impl requiring >1 record to return True.
    """
    assert has_problems_for_class([_p("only")], "only") is True


def test_empty_problems_returns_false() -> None:
    """Empty problems list returns False."""
    assert has_problems_for_class([], "any") is False


def test_false_when_no_record_matches() -> None:
    """Returns False when problems exist but none match the target class.

    Kills impl returning True for any non-empty input.
    """
    problems = [_p("alpha"), _p("beta"), _p("gamma")]
    assert has_problems_for_class(problems, "delta") is False
