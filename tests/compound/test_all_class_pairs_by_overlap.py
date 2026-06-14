"""Item 289: all_class_pairs_by_overlap() — ranked class pairs by shared finding_id count (2026-06-08).

``all_class_pairs_by_overlap(problems: list[Problem]) -> list[tuple[str, str, int]]``:
Returns all pairs of distinct classes sorted by overlap count descending.
Canonical pair ordering: cls_a < cls_b alphabetically.  Ties broken by
(cls_a, cls_b) ascending.  0-overlap pairs included.
Empty or single-class input -> [].  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: highest-overlap pair appears first.
     Kills impl returning arbitrary (e.g. insertion) order.
  2. Canonical pair ordering cls_a < cls_b (never reversed).
     Kills impl that may emit (beta, alpha) as a pair.
  3. Zero-overlap pairs included in result.
     Kills impl that filters to count > 0 only.
  4. Single class -> [] (no self-pairs, no cross-pairs possible).
     Kills impl that emits (cls, cls) self-pairs or raises.
  5. Return is list[tuple[str, str, int]] — three-element tuples.
     Kills impl returning dict or two-element tuples.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    all_class_pairs_by_overlap,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_highest_overlap_pair_first() -> None:
    """Pair with most shared ids appears first in result.

    PRIMARY DISCRIMINATOR: kills impl returning insertion order.
    alpha-beta share 2 ids; alpha-gamma share 0; beta-gamma share 1.
    Expected order: (alpha,beta,2), (beta,gamma,1), (alpha,gamma,0).
    """
    problems = [
        _p("alpha", "shared_ab_1"),
        _p("alpha", "shared_ab_2"),
        _p("alpha", "only_alpha"),
        _p("beta", "shared_ab_1"),
        _p("beta", "shared_ab_2"),
        _p("beta", "shared_bg"),
        _p("gamma", "shared_bg"),
        _p("gamma", "only_gamma"),
    ]
    result = all_class_pairs_by_overlap(problems)
    assert result[0] == ("alpha", "beta", 2), "alpha-beta share 2 ids -> first; got " + repr(result)
    assert result[1] == ("beta", "gamma", 1), "beta-gamma share 1 id -> second; got " + repr(result)
    assert result[2] == ("alpha", "gamma", 0), "alpha-gamma share 0 ids -> third; got " + repr(
        result
    )


def test_canonical_pair_ordering_cls_a_lt_cls_b() -> None:
    """Each pair has cls_a < cls_b alphabetically — never reversed.

    Kills impl that may emit (beta, alpha) for the beta-alpha pair.
    """
    problems = [
        _p("beta", "shared"),
        _p("alpha", "shared"),
    ]
    result = all_class_pairs_by_overlap(problems)
    assert len(result) == 1, "One pair from two classes; got " + repr(result)
    cls_a, cls_b, _ = result[0]
    assert cls_a < cls_b, (
        "Canonical ordering: cls_a < cls_b; got (" + repr(cls_a) + ", " + repr(cls_b) + ")"
    )
    assert cls_a == "alpha" and cls_b == "beta", "Expected ('alpha', 'beta'); got " + repr(
        result[0]
    )


def test_zero_overlap_pairs_included() -> None:
    """Pairs with 0 shared ids are still included in result.

    Kills impl filtering to count > 0 only.
    alpha and beta share nothing -> (alpha, beta, 0) in result.
    """
    problems = [
        _p("alpha", "id_a"),
        _p("beta", "id_b"),
    ]
    result = all_class_pairs_by_overlap(problems)
    assert len(result) == 1, "One pair; got " + repr(result)
    assert result[0] == ("alpha", "beta", 0), "Zero-overlap pair included; got " + repr(result[0])


def test_single_class_returns_empty_list() -> None:
    """Single class -> [] — no pairs possible.

    Kills impl that raises or returns self-pair (cls, cls, n).
    """
    problems = [_p("alpha", "id1"), _p("alpha", "id2")]
    result = all_class_pairs_by_overlap(problems)
    assert result == [], "Single class -> []; got " + repr(result)


def test_return_type_is_list_of_three_tuples() -> None:
    """Return type is list[tuple[str, str, int]] — 3-element tuples.

    Kills impl returning dict or 2-element tuples.
    """
    problems = [_p("alpha", "shared"), _p("beta", "shared")]
    result = all_class_pairs_by_overlap(problems)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 1, "One pair; got " + repr(result)
    pair = result[0]
    assert isinstance(pair, tuple) and len(pair) == 3, (
        "Each element must be a 3-tuple; got " + repr(pair)
    )
    cls_a, cls_b, count = pair
    assert isinstance(cls_a, str) and isinstance(cls_b, str) and isinstance(count, int), (
        "Tuple must be (str, str, int); got types " + repr((type(cls_a), type(cls_b), type(count)))
    )
