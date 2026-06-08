"""Item 211: has_duplicate_finding_ids() — duplicate-id presence check (2026-06-08).

``has_duplicate_finding_ids(problems: list[Problem])``
-> ``bool``:
Returns ``True`` iff any finding_id appears more than once.
Empty -> ``False``.  All distinct -> ``False``.  Pure; no I/O.

The boolean face of :func:`count_unique_finding_ids` (item 210)::

    if has_duplicate_finding_ids(findings):
        warn("duplicate finding ids detected")

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: duplicate present -> True.
     Kills an impl that always returns False.
  2. All distinct -> False (not True).
     Kills an impl that always returns True.
  3. Empty list -> False (not raises, not True).
     Kills an impl that raises IndexError or returns True on empty.
  4. Return type is bool (not int, not None).
     Kills an impl that returns the count or None.
  5. Single duplicate among many distincts -> True.
     Kills an impl that requires all ids to be duplicate.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    has_duplicate_finding_ids,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_duplicate_present_returns_true() -> None:
    """Duplicate finding_id -> True.

    PRIMARY DISCRIMINATOR: kills an impl that always returns False.
    Two problems with the same finding_id must yield True.
    """
    p = Problem(problem_class="alpha", finding_id="shared:1")
    problems = [p, p]

    result = has_duplicate_finding_ids(problems)

    assert result is True, "two problems sharing the same finding_id must return True; got " + repr(
        result
    )


def test_all_distinct_returns_false() -> None:
    """All distinct finding_ids -> False.

    Kills an impl that always returns True.
    """
    problems = [_p("alpha", i) for i in range(5)]

    result = has_duplicate_finding_ids(problems)

    assert result is False, "all distinct finding_ids must return False; got " + repr(result)


def test_empty_list_returns_false() -> None:
    """Empty list -> False (not raises, not True).

    Kills an impl that raises IndexError or misidentifies empty as duplicate.
    """
    result = has_duplicate_finding_ids([])

    assert result is False, "empty input must return False; got " + repr(result)


def test_return_type_is_bool() -> None:
    """Return value is bool, not int or None.

    Kills an impl that returns the duplicate count or None.
    """
    problems = [_p("alpha")]

    result = has_duplicate_finding_ids(problems)

    assert isinstance(result, bool), "return type must be bool; got " + repr(type(result))


def test_single_duplicate_among_distincts_returns_true() -> None:
    """One duplicate among many distinct ids -> True.

    Kills an impl that requires ALL ids to be duplicate (some misread of
    the contract as 'all-or-nothing').
    """
    problems = [
        Problem(problem_class="a", finding_id="id:1"),  # appears twice
        Problem(problem_class="b", finding_id="id:2"),
        Problem(problem_class="c", finding_id="id:3"),
        Problem(problem_class="d", finding_id="id:1"),  # duplicate of first
    ]

    result = has_duplicate_finding_ids(problems)

    assert result is True, "one duplicate among distincts must return True; got " + repr(result)
