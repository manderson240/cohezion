"""Item 414: repeated_finding_ids() — fids appearing in two or more records (2026-06-08).

``repeated_finding_ids(problems) -> frozenset[str]``:
Returns frozenset of finding_ids with a total count >= 2 in the dataset.
Empty -> frozenset().  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns fids with count EXACTLY >= 2 (excludes singletons).
     Kills impl returning all fids (including singletons).
  2. Returns FROZENSET[str] of fids (not Problem objects, not counts).
     Kills impl returning Problem objects.
  3. Empty -> frozenset() (not raise).
  4. All-singleton dataset -> frozenset() (no repeated fids).
     Kills impl always returning something.
  5. Only deduplicates by fid, not by class.
     Kills impl requiring same class for repetition.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    repeated_finding_ids,
)


def _p(fid: str, cls: str = "cls") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_only_fids_with_count_two_or_more() -> None:
    """Returns frozenset of fids with count >= 2, not singletons.

    PRIMARY DISCRIMINATOR: kills impl returning all fids.
    """
    problems = [_p("once"), _p("twice"), _p("twice")]
    result = repeated_finding_ids(problems)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert result == frozenset({"twice"}), "only 'twice' (count=2); got " + repr(result)


def test_returns_frozenset_of_fid_strings() -> None:
    """Returns frozenset[str], not list or Problem objects."""
    problems = [_p("a"), _p("a"), _p("b")]
    result = repeated_finding_ids(problems)
    assert isinstance(result, frozenset)
    assert all(isinstance(x, str) for x in result)


def test_empty_returns_empty_frozenset() -> None:
    """Empty input returns frozenset(), not raise."""
    result = repeated_finding_ids([])
    assert result == frozenset(), "Empty -> frozenset(); got " + repr(result)


def test_all_singletons_returns_empty_frozenset() -> None:
    """All-singleton dataset -> frozenset() (no repeated fids).

    Kills impl always returning something.
    """
    problems = [_p("x"), _p("y"), _p("z")]
    result = repeated_finding_ids(problems)
    assert result == frozenset(), "All singletons -> frozenset(); got " + repr(result)


def test_cross_class_repetition_counts() -> None:
    """fid in two different classes counts as repeated.

    Kills impl requiring same class for repetition.
    """
    p0 = _p("shared", "classA")
    p1 = _p("shared", "classB")
    result = repeated_finding_ids([p0, p1])
    assert result == frozenset({"shared"}), "shared in 2 classes = repeated; got " + repr(result)
