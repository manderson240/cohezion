"""Item 411: problems_exceeding_threshold() — records whose fid count exceeds threshold (2026-06-08).

``problems_exceeding_threshold(problems, threshold) -> list[Problem]``:
Returns Problem records whose finding_id has a total record count >= threshold
in the full dataset (using finding_id_histogram to compute counts).
threshold=0 or threshold=1 -> all records.
Empty -> [].  Preserves input order.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: filters by fid's TOTAL count in dataset, not per-class count.
     Kills impl using problem_count_for_class instead of finding_id_histogram.
  2. Returns LIST[Problem] objects, not fids or counts.
     Kills impl returning the filtered fids list.
  3. threshold=1 returns all records (every fid has >= 1 occurrence).
     Validates boundary behavior.
  4. Empty input -> [].
     Kills impl raising on empty.
  5. Input order preserved in returned list.
     Kills impl that reorders results.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_exceeding_threshold,
)


def _p(fid: str, cls: str = "cls") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_filters_by_fid_total_count_in_dataset() -> None:
    """Records filtered by fid's total count across ALL classes.

    PRIMARY DISCRIMINATOR: fid 'shared' has 2 total records (1 in alpha, 1 in beta).
    threshold=2 -> both records for 'shared' included; 'unique' (count=1) excluded.
    """
    p0 = _p("shared", "alpha")
    p1 = _p("shared", "beta")
    p2 = _p("unique", "alpha")
    result = problems_exceeding_threshold([p0, p1, p2], threshold=2)
    fids = {p.finding_id for p in result}
    assert fids == {"shared"}, "Only shared (count=2) >= threshold(2); got " + repr(fids)
    assert len(result) == 2, "Both shared records returned; got " + repr(len(result))


def test_returns_list_of_problem_objects() -> None:
    """Returns list[Problem], not list of fids or counts."""
    p0 = _p("fid", "cls1")
    result = problems_exceeding_threshold([p0], threshold=1)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert all(isinstance(p, Problem) for p in result)


def test_threshold_one_returns_all_records() -> None:
    """threshold=1 -> all records returned (every fid has >= 1 occurrence)."""
    problems = [_p("a"), _p("b"), _p("c")]
    result = problems_exceeding_threshold(problems, threshold=1)
    assert len(result) == 3, "All 3 records returned at threshold=1; got " + repr(len(result))


def test_empty_returns_empty_list() -> None:
    """Empty input returns []."""
    assert problems_exceeding_threshold([], threshold=2) == []


def test_input_order_preserved() -> None:
    """Input order is preserved in the returned list."""
    p0 = _p("multi", "cls1")
    p1 = _p("multi", "cls2")
    p2 = _p("multi", "cls3")
    result = problems_exceeding_threshold([p0, p1, p2], threshold=2)
    assert result[0] is p0
    assert result[1] is p1
    assert result[2] is p2
