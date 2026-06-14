"""Item 352: classes_with_finding_id_overlap() -- class pairs sharing a finding_id (2026-06-08).

``classes_with_finding_id_overlap(problems) -> frozenset[frozenset[str]]``:
Returns frozenset of 2-element frozensets, each pair being two classes that
share at least one finding_id.  No self-pairs.  3+ classes sharing one
finding_id -> C(n,2) pairs.  Empty -> frozenset().  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: returns PAIRS (frozensets of 2) not flat class set.
     Kills impl returning frozenset of class names.
  2. Pair is frozenset (unordered) not tuple.
     Kills impl returning sorted tuples.
  3. 3 classes sharing a finding_id -> 3 pairs C(3,2).
     Kills impl that only detects first pair.
  4. No sharing -> frozenset().
     Kills impl returning all class combinations.
  5. Empty input -> frozenset().
     Kills impl raising on empty.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_with_finding_id_overlap,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_pairs_not_flat_class_set() -> None:
    """Returns frozenset of 2-element frozensets, not a flat frozenset of names.

    PRIMARY DISCRIMINATOR: kills impl returning frozenset({'alpha', 'beta'}).
    alpha and beta share F001 -> {{alpha, beta}}.
    """
    problems = [_p("alpha", "F001"), _p("beta", "F001")]
    result = classes_with_finding_id_overlap(problems)
    assert isinstance(result, frozenset), "Must be frozenset; got " + repr(type(result))
    assert len(result) == 1, "1 overlapping pair; got " + repr(result)
    pair = next(iter(result))
    assert isinstance(pair, frozenset), "Inner element must be frozenset; got " + repr(type(pair))
    assert pair == frozenset({"alpha", "beta"}), "Pair is alpha+beta; got " + repr(pair)


def test_pair_is_frozenset_not_tuple() -> None:
    """Inner pairs are frozensets not tuples.

    Kills impl using sorted tuples (('alpha', 'beta') instead of frozenset).
    """
    problems = [_p("alpha", "F001"), _p("beta", "F001")]
    result = classes_with_finding_id_overlap(problems)
    for pair in result:
        assert isinstance(pair, frozenset), "Pair must be frozenset; got " + repr(type(pair))
        assert len(pair) == 2, "Pair has 2 elements; got " + repr(len(pair))


def test_three_classes_sharing_finding_id_produces_three_pairs() -> None:
    """3 classes sharing one finding_id -> C(3,2)=3 pairs.

    Kills impl that only emits the first pair found.
    """
    problems = [_p("alpha", "F001"), _p("beta", "F001"), _p("gamma", "F001")]
    result = classes_with_finding_id_overlap(problems)
    assert len(result) == 3, "C(3,2)=3 pairs; got " + repr(result)
    assert frozenset({"alpha", "beta"}) in result
    assert frozenset({"alpha", "gamma"}) in result
    assert frozenset({"beta", "gamma"}) in result


def test_no_sharing_returns_empty_frozenset() -> None:
    """Disjoint finding_ids -> frozenset().

    Kills impl returning all class combinations.
    """
    problems = [_p("alpha", "F001"), _p("beta", "F002")]
    result = classes_with_finding_id_overlap(problems)
    assert result == frozenset(), "No overlap -> frozenset(); got " + repr(result)


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input returns frozenset() without raising."""
    assert classes_with_finding_id_overlap([]) == frozenset()
