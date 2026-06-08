"""Item 302: top_growing_classes() — classes with largest positive delta (2026-06-08).

``top_growing_classes(scan_a, scan_b, n=5) -> list[tuple[str, int]]``:
Returns list of (class, delta) for classes where delta > 0, sorted by delta
descending.  Ties broken by class name ascending.  n limits result length.
n=0 -> [].  Empty or no positive-delta classes -> [].  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only classes with delta > 0 included (not >= 0).
     Kills impl including unchanged (delta=0) or shrinking classes.
  2. Sorted by delta descending (highest growth first).
     Kills impl returning arbitrary or ascending order.
  3. n=0 -> [] (not all classes).
     Kills impl ignoring n when n=0.
  4. Tie-break: class name ascending.
     Kills impl with wrong tie-break direction.
  5. Return type is list[tuple[str, int]].
     Kills impl returning dict or frozenset.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_growing_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_only_positive_delta_classes_included() -> None:
    """Only classes with delta > 0 are in result; delta=0 and delta<0 excluded.

    PRIMARY DISCRIMINATOR: kills impl using >= 0 or including all classes.
    alpha: grows (1->3, delta=+2).
    beta: stable (2->2, delta=0) -> excluded.
    gamma: shrinks (3->1, delta=-2) -> excluded.
    """
    scan_a = [
        _p("alpha", 0),
        _p("beta", 0),
        _p("beta", 1),
        _p("gamma", 0),
        _p("gamma", 1),
        _p("gamma", 2),
    ]
    scan_b = [
        _p("alpha", 0),
        _p("alpha", 1),
        _p("alpha", 2),
        _p("beta", 0),
        _p("beta", 1),
        _p("gamma", 0),
    ]
    result = top_growing_classes(scan_a, scan_b)
    class_names = [c for c, _ in result]
    assert "alpha" in class_names, "alpha grew (delta=+2) -> in result; got " + repr(class_names)
    assert "beta" not in class_names, "beta stable (delta=0) -> excluded; got " + repr(class_names)
    assert "gamma" not in class_names, "gamma shrank (delta=-2) -> excluded; got " + repr(
        class_names
    )


def test_sorted_by_delta_descending() -> None:
    """Highest-delta class appears first.

    Kills impl returning arbitrary or ascending order.
    alpha delta=+3, beta delta=+1 -> alpha first.
    """
    scan_a = [_p("beta", 0)]
    scan_b = [
        _p("alpha", 0),
        _p("alpha", 1),
        _p("alpha", 2),  # alpha: 0->3, delta=+3
        _p("beta", 0),
        _p("beta", 1),  # beta: 1->2, delta=+1
    ]
    result = top_growing_classes(scan_a, scan_b)
    assert len(result) == 2, "Two growing classes; got " + repr(result)
    assert result[0] == ("alpha", 3), "alpha has highest delta (+3) -> first; got " + repr(
        result[0]
    )
    assert result[1] == ("beta", 1), "beta has delta +1 -> second; got " + repr(result[1])


def test_n_zero_returns_empty_list() -> None:
    """n=0 -> [] regardless of input.

    Kills impl ignoring n when n=0.
    """
    scan_a = []
    scan_b = [_p("alpha", 0), _p("alpha", 1)]
    result = top_growing_classes(scan_a, scan_b, n=0)
    assert result == [], "n=0 -> []; got " + repr(result)


def test_tie_break_by_class_name_ascending() -> None:
    """Tie in delta broken by class name ascending (alphabetically smallest first).

    Kills impl with wrong tie-break direction.
    alpha delta=+2, beta delta=+2 -> alpha (smaller name) comes first.
    """
    scan_a = []
    scan_b = [_p("beta", 0), _p("beta", 1), _p("alpha", 0), _p("alpha", 1)]
    result = top_growing_classes(scan_a, scan_b)
    assert len(result) == 2, "Two classes; got " + repr(result)
    assert result[0][0] == "alpha", "alpha < beta alphabetically -> first on tie; got " + repr(
        result[0][0]
    )
    assert result[1][0] == "beta", "beta -> second on tie; got " + repr(result[1][0])


def test_return_type_is_list_of_tuples() -> None:
    """Return type is list[tuple[str, int]].

    Kills impl returning dict or frozenset.
    """
    scan_a = []
    scan_b = [_p("alpha", 0)]
    result = top_growing_classes(scan_a, scan_b)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 1
    pair = result[0]
    assert isinstance(pair, tuple) and len(pair) == 2, "Each element must be 2-tuple; got " + repr(
        pair
    )
    cls, delta = pair
    assert isinstance(cls, str) and isinstance(delta, int), "Tuple must be (str, int); got " + repr(
        (type(cls), type(delta))
    )
