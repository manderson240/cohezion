"""Item 412: problems_below_threshold() — records whose fid count is below threshold (2026-06-08).

``problems_below_threshold(problems, threshold) -> list[Problem]``:
Returns Problem records whose finding_id has a total record count < threshold.
threshold=0 or threshold=1 -> [].
Empty -> [].  Preserves input order.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: threshold=0 returns [] (no fid has count < 0).
     Kills impl that flips >= to <= instead of strict <.
  2. threshold=1 returns [] (every fid count >= 1).
     Kills impl that treats 'below' as '<=' instead of '<'.
  3. threshold=2 returns only singleton fids.
     Validates core semantics.
  4. Empty input -> [].
     Kills impl raising on empty.
  5. Input order preserved.
     Kills impl that reorders.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_below_threshold,
)


def _p(fid: str, cls: str = "cls") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_threshold_zero_returns_empty() -> None:
    """threshold=0 returns [] since no fid count can be < 0.

    PRIMARY DISCRIMINATOR: kills impl using <= instead of <.
    """
    problems = [_p("a"), _p("b"), _p("c")]
    result = problems_below_threshold(problems, threshold=0)
    assert result == [], "threshold=0 -> []; got " + repr(result)


def test_threshold_one_returns_empty() -> None:
    """threshold=1 returns [] since every fid appears at least once.

    Kills impl treating below as inclusive.
    """
    problems = [_p("a"), _p("b"), _p("b")]
    result = problems_below_threshold(problems, threshold=1)
    assert result == [], "threshold=1 -> []; got " + repr(result)


def test_threshold_two_returns_singleton_fids() -> None:
    """threshold=2 returns only records whose fid appears exactly once."""
    p0 = _p("once", "cls1")
    p1 = _p("twice", "cls1")
    p2 = _p("twice", "cls2")
    result = problems_below_threshold([p0, p1, p2], threshold=2)
    fids = {p.finding_id for p in result}
    assert fids == {"once"}, "only 'once' (count=1) < threshold(2); got " + repr(fids)
    assert len(result) == 1


def test_empty_returns_empty_list() -> None:
    """Empty input returns []."""
    assert problems_below_threshold([], threshold=3) == []


def test_input_order_preserved() -> None:
    """Input order is preserved in the returned list."""
    p0 = _p("rare1", "cls1")
    p1 = _p("rare2", "cls1")
    p2 = _p("rare3", "cls1")
    result = problems_below_threshold([p0, p1, p2], threshold=2)
    assert result[0] is p0
    assert result[1] is p1
    assert result[2] is p2
