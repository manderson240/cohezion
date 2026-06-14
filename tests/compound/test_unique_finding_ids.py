"""Item 263: unique_finding_ids() — frozenset of all finding_ids in a scan (2026-06-08).

``unique_finding_ids(problems: list[Problem]) -> frozenset[str]``:
Returns the frozenset of all ``finding_id`` values across the input problems.
Each id appears exactly once even if duplicated in the input.
Empty input -> frozenset().  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns a frozenset of finding_ids, not an int dedup count.
     Kills impl returning len(set(p.finding_id for p in problems)).
  2. Duplicated finding_ids appear only once in the result.
     Kills impl that returns a multiset or list.
  3. Empty input -> frozenset().
     Kills impl that raises on empty input.
  4. Return type is frozenset[str], not list or set.
     Kills impl returning a plain set or list.
  5. All finding_ids are present; nothing is dropped.
     Kills impl that filters or transforms ids.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    unique_finding_ids,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_frozenset_not_count() -> None:
    """Returns frozenset of ids, not an int count.

    PRIMARY DISCRIMINATOR: kills impl returning len(set(ids)).
    Two distinct finding_ids -> frozenset of size 2, not int 2.
    """
    problems = [_p("alpha", "a:1"), _p("beta", "b:1")]
    result = unique_finding_ids(problems)
    assert result == frozenset({"a:1", "b:1"}), "Must return frozenset of ids; got " + repr(result)


def test_duplicate_ids_appear_once() -> None:
    """Duplicated finding_ids appear only once.

    Kills impl returning a multiset or list with duplicates.
    """
    problems = [
        _p("alpha", "x:1"),
        _p("alpha", "x:1"),  # duplicate
        _p("beta", "y:1"),
    ]
    result = unique_finding_ids(problems)
    assert result == frozenset({"x:1", "y:1"}), "Duplicate id 'x:1' must appear once; got " + repr(
        result
    )
    assert len(result) == 2


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input -> frozenset().

    Kills impl that raises on empty input.
    """
    result = unique_finding_ids([])
    assert result == frozenset(), "Empty input -> frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset, not set or list.

    Kills impl returning a plain mutable set or list.
    """
    problems = [_p("alpha", "a:0"), _p("alpha", "a:1")]
    result = unique_finding_ids(problems)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))


def test_all_ids_present_nothing_dropped() -> None:
    """All distinct finding_ids are in the result; nothing dropped.

    Kills impl that filters or transforms ids.
    """
    ids = {f"cls:{i}" for i in range(10)}
    problems = [_p("alpha", fid) for fid in ids]
    result = unique_finding_ids(problems)
    assert result == frozenset(ids), "All 10 ids must appear; got " + repr(result)
