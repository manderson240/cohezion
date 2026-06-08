"""Item 428: class_pair_co_occurrence() — distinct fids in both classes (2026-06-08).

``class_pair_co_occurrence(problems, class_a, class_b) -> int``:
Returns the count of distinct finding_ids that appear in BOTH class_a AND class_b.
Empty or unknown class -> 0.  class_a == class_b -> distinct fids in that class.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts DISTINCT finding_ids in intersection (not total records).
     Kills impl counting records instead of distinct fids.
  2. Unknown class returns 0, not raise.
     Kills impl raising KeyError on absent class.
  3. class_a == class_b -> distinct fids in that class.
     Validates self-intersection edge case.
  4. Empty problems -> 0.
     Kills impl raising on empty.
  5. Overlapping fids correctly counted.
     Validates core set-intersection logic.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_pair_co_occurrence,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_counts_distinct_fids_not_records() -> None:
    """Counts distinct fids in intersection, not number of records.

    PRIMARY DISCRIMINATOR: 'shared' appears twice in class_a and once in class_b,
    but counts as 1 distinct fid in the intersection.
    """
    problems = [
        _p("class_a", "shared"),
        _p("class_a", "shared"),  # duplicate record of same fid
        _p("class_b", "shared"),
        _p("class_a", "only_a"),
    ]
    result = class_pair_co_occurrence(problems, "class_a", "class_b")
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 1, "1 distinct shared fid; got " + repr(result)


def test_unknown_class_returns_zero() -> None:
    """Unknown class returns 0, not raise."""
    problems = [_p("alpha", "F001")]
    result = class_pair_co_occurrence(problems, "alpha", "UNKNOWN")
    assert result == 0, "Unknown class -> 0; got " + repr(result)


def test_self_intersection_returns_distinct_fid_count() -> None:
    """class_a == class_b -> distinct fids in that class."""
    problems = [
        _p("alpha", "F001"),
        _p("alpha", "F001"),  # duplicate
        _p("alpha", "F002"),
        _p("beta", "F003"),
    ]
    result = class_pair_co_occurrence(problems, "alpha", "alpha")
    assert result == 2, "alpha has 2 distinct fids (F001, F002); got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty problems returns 0."""
    result = class_pair_co_occurrence([], "alpha", "beta")
    assert result == 0, "Empty -> 0; got " + repr(result)


def test_multiple_shared_fids() -> None:
    """Multiple shared fids correctly counted."""
    problems = [
        _p("cls_x", "fid1"),
        _p("cls_x", "fid2"),
        _p("cls_x", "fid3"),
        _p("cls_y", "fid2"),
        _p("cls_y", "fid3"),
        _p("cls_y", "fid4"),
    ]
    result = class_pair_co_occurrence(problems, "cls_x", "cls_y")
    assert result == 2, "fid2 and fid3 shared; got " + repr(result)
