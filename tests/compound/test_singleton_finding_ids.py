"""Item 413: singleton_finding_ids() — fids that appear in exactly one record (2026-06-08).

``singleton_finding_ids(problems) -> frozenset[str]``:
Returns frozenset of finding_ids whose total count in the dataset is exactly 1.
Empty -> frozenset().  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns fids with count EXACTLY 1 (not <= 1 or <= 2).
     Kills impl using <= instead of ==.
  2. Returns FROZENSET[str] (not list, not set of Problem objects).
     Kills impl returning Problem objects.
  3. fids with count >= 2 are excluded.
     Kills impl returning all fids.
  4. Empty -> frozenset() (not raise).
     Kills impl raising on empty histogram.
  5. All-singleton dataset -> frozenset of all fids.
     Validates complete coverage.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    singleton_finding_ids,
)


def _p(fid: str, cls: str = "cls") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_only_count_one_fids() -> None:
    """Returns frozenset of fids with count EXACTLY 1.

    PRIMARY DISCRIMINATOR: kills impl using <= threshold.
    """
    problems = [_p("once"), _p("twice"), _p("twice")]
    result = singleton_finding_ids(problems)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert result == frozenset({"once"}), "only 'once' (count=1); got " + repr(result)


def test_returns_frozenset_not_list() -> None:
    """Returns frozenset, not list or set of Problem objects."""
    problems = [_p("solo")]
    result = singleton_finding_ids(problems)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert result == frozenset({"solo"})


def test_repeated_fids_excluded() -> None:
    """fids appearing >= 2 times are excluded.

    Kills impl returning all fids.
    """
    problems = [_p("a"), _p("a"), _p("b"), _p("b"), _p("b"), _p("c")]
    result = singleton_finding_ids(problems)
    assert result == frozenset({"c"}), "only 'c' is singleton; got " + repr(result)


def test_empty_returns_empty_frozenset() -> None:
    """Empty input returns frozenset(), not raise."""
    result = singleton_finding_ids([])
    assert result == frozenset(), "Empty -> frozenset(); got " + repr(result)


def test_all_singletons_returns_all_fids() -> None:
    """All-singleton dataset -> frozenset of all fids."""
    problems = [_p("x"), _p("y"), _p("z")]
    result = singleton_finding_ids(problems)
    assert result == frozenset({"x", "y", "z"}), "All 3 singletons; got " + repr(result)
