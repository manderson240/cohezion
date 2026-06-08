"""Item 406: unique_finding_ids_count() — distinct finding_id cardinality (2026-06-08).

``unique_finding_ids_count(problems) -> int``:
Returns the count of distinct finding_id values across all records.
Same fid appearing in multiple classes counts as 1 distinct fid.
Empty -> 0.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: same fid in 2 classes counts as 1 distinct fid (not 2).
     Kills impl counting records instead of distinct fids.
  2. Returns INTEGER, not frozenset.
     Kills impl returning the frozenset of fids.
  3. Empty -> 0.
     Kills impl raising on empty.
  4. Single fid with many records -> 1.
     Kills impl using len(problems).
  5. Matches manual frozenset cardinality.
     Validates composition invariant.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    unique_finding_ids_count,
)


def _p(fid: str, cls: str = "cls") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_same_fid_in_two_classes_counts_as_one() -> None:
    """Same fid in 2 classes counts as 1 distinct fid.

    PRIMARY DISCRIMINATOR: kills impl counting records.
    """
    problems = [_p("shared", "alpha"), _p("shared", "beta"), _p("unique", "alpha")]
    result = unique_finding_ids_count(problems)
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 2, "2 distinct fids (shared, unique); got " + repr(result)


def test_returns_integer_not_frozenset() -> None:
    """Returns int, not frozenset.

    Kills impl returning the frozenset of fids.
    """
    result = unique_finding_ids_count([_p("a"), _p("b")])
    assert isinstance(result, int), "Must return int; got " + repr(type(result))


def test_empty_returns_zero() -> None:
    """Empty input returns 0."""
    assert unique_finding_ids_count([]) == 0


def test_single_fid_many_records_returns_one() -> None:
    """Single fid repeated many times -> 1."""
    problems = [_p("same", f"cls{i}") for i in range(5)]
    result = unique_finding_ids_count(problems)
    assert result == 1, "Only 1 distinct fid; got " + repr(result)


def test_matches_manual_frozenset_cardinality() -> None:
    """Result equals len of the frozenset of fids.

    Validates composition invariant.
    """
    problems = [_p("a"), _p("b"), _p("c"), _p("a"), _p("b")]
    result = unique_finding_ids_count(problems)
    expected = len(frozenset(p.finding_id for p in problems))
    assert result == expected, "Must match frozenset cardinality; got " + repr(result)
