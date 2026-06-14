"""Item 217: count_problems_added_since() — recency prefix count (2026-06-08).

``count_problems_added_since(problems: list[Problem], id_prefixes: set[str])``
-> ``int``:
Counts Problems whose ``finding_id`` starts with ANY prefix in *id_prefixes*.
Models "how many NEW problems were found in this scan?" when scan IDs share a
common prefix (e.g. ``"scan-2026-06-08:"``).
Empty *id_prefixes* -> ``0``.  Empty *problems* -> ``0``.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only Problems whose finding_id starts with a prefix are counted.
     Kills an impl that returns len(problems) (counts all regardless of prefix).
  2. Multiple prefixes -- a Problem matching ANY prefix is counted exactly once.
     Kills an impl that counts the same Problem multiple times (one per prefix match).
  3. Empty id_prefixes -> 0.
     Kills an impl that returns len(problems) when prefixes is empty.
  4. Empty problems -> 0.
     Kills an impl that raises or returns None on empty input.
  5. Return type is int.
     Kills an impl that returns a list or set.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    count_problems_added_since,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_only_prefix_matching_problems_counted() -> None:
    """Only Problems with matching finding_id prefix are counted.

    PRIMARY DISCRIMINATOR: kills an impl that returns len(problems).
    Two problems share prefix "scan-A:", one does not.
    """
    problems = [
        _p("alpha", "scan-A:001"),
        _p("alpha", "scan-A:002"),
        _p("beta", "scan-B:001"),  # different prefix
    ]
    result = count_problems_added_since(problems, {"scan-A:"})
    assert result == 2, "Only 2 problems match prefix 'scan-A:'; got " + repr(result)


def test_problem_counted_once_even_if_multiple_prefixes_match() -> None:
    """A Problem matching more than one prefix is counted exactly once.

    Kills an impl that sums matches per prefix rather than counting distinct Problems.
    """
    # "scan-A:001" starts with both "scan-" and "scan-A"
    problems = [_p("alpha", "scan-A:001")]
    result = count_problems_added_since(problems, {"scan-", "scan-A"})
    assert result == 1, "Problem matching 2 prefixes must be counted once; got " + repr(result)


def test_empty_prefixes_returns_zero() -> None:
    """Empty id_prefixes -> 0, not len(problems).

    Kills an impl that returns total count when no filter is specified.
    """
    problems = [_p("alpha", "scan-A:001"), _p("beta", "scan-B:002")]
    result = count_problems_added_since(problems, set())
    assert result == 0, "Empty prefixes must return 0; got " + repr(result)


def test_empty_problems_returns_zero() -> None:
    """Empty problems list -> 0.

    Kills an impl that raises or returns None on empty input.
    """
    result = count_problems_added_since([], {"scan-A:"})
    assert result == 0, "Empty problems must return 0; got " + repr(result)


def test_return_type_is_int() -> None:
    """Return value is int, not list or set.

    Kills an impl that returns the matching Problem objects instead of a count.
    """
    problems = [_p("alpha", "scan-A:001")]
    result = count_problems_added_since(problems, {"scan-A:"})
    assert isinstance(result, int), "Return type must be int; got " + repr(type(result))
    assert result == 1
