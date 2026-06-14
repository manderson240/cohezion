"""Item 303: top_shrinking_classes() — classes with the largest negative delta (2026-06-08).

``top_shrinking_classes(scan_a, scan_b, n=5) -> list[tuple[str, int]]``:
Returns list of (class, delta) for classes with the most negative delta
(count_b - count_a < 0), sorted ascending by delta (most negative first),
ties broken by class name ascending.  n limits result length.
n=0 → [].  No shrinkage → [].  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only classes with delta < 0 included.
     Kills impl including unchanged (delta=0) or growing (delta>0) classes.
  2. Sorted ascending by delta (most negative / most improved first).
     Kills impl sorted descending or by class name first.
  3. n limits the result to at most n items.
     Kills impl ignoring the n parameter.
  4. n=0 → [] regardless of shrinkage.
     Kills impl returning [] only when no shrinkage exists.
  5. Tie-break: classes with equal delta sorted by class name ascending.
     Kills impl using reverse tie-breaking.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_shrinking_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_only_negative_delta_classes_included() -> None:
    """Only classes with delta < 0 are in result; delta=0 and delta>0 excluded.

    PRIMARY DISCRIMINATOR: kills impl using <= 0 or including all classes.
    alpha: shrinks (3→1, delta=-2).
    beta:  stable  (2→2, delta=0)  -> excluded.
    gamma: grows   (1→3, delta=+2) -> excluded.
    Only alpha should appear.
    """
    scan_a = [
        _p("alpha", 0),
        _p("alpha", 1),
        _p("alpha", 2),
        _p("beta", 0),
        _p("beta", 1),
        _p("gamma", 0),
    ]
    scan_b = [
        _p("alpha", 0),
        _p("beta", 0),
        _p("beta", 1),
        _p("gamma", 0),
        _p("gamma", 1),
        _p("gamma", 2),
    ]
    result = top_shrinking_classes(scan_a, scan_b)
    class_names = [c for c, _ in result]
    assert "alpha" in class_names, "alpha shrank (delta=-2) -> in result; got " + repr(result)
    assert "beta" not in class_names, "beta stable (delta=0) -> excluded; got " + repr(result)
    assert "gamma" not in class_names, "gamma grew (delta=+2) -> excluded; got " + repr(result)


def test_sorted_ascending_by_delta_most_negative_first() -> None:
    """Most negative delta class appears first.

    Kills impl sorted descending.
    alpha delta=-3, beta delta=-1 -> alpha first (most improved).
    """
    scan_a = [
        _p("alpha", 0),
        _p("alpha", 1),
        _p("alpha", 2),  # alpha: 3→0, delta=-3
        _p("beta", 0),
        _p("beta", 1),  # beta:  2→1, delta=-1
    ]
    scan_b = [
        _p("beta", 0),
    ]
    result = top_shrinking_classes(scan_a, scan_b)
    assert len(result) == 2, "Two shrinking classes; got " + repr(result)
    assert result[0] == ("alpha", -3), "alpha delta=-3 most negative -> first; got " + repr(
        result[0]
    )
    assert result[1] == ("beta", -1), "beta delta=-1 -> second; got " + repr(result[1])


def test_n_limits_result_length() -> None:
    """n limits the number of returned classes.

    Kills impl ignoring the n parameter.
    Three shrinking classes but n=2 -> only top 2 (most negative).
    """
    scan_a = [
        _p("alpha", 0),
        _p("alpha", 1),
        _p("alpha", 2),  # delta=-3
        _p("beta", 0),
        _p("beta", 1),  # delta=-2
        _p("gamma", 0),  # delta=-1
    ]
    scan_b = []
    result = top_shrinking_classes(scan_a, scan_b, n=2)
    assert len(result) == 2, f"n=2 -> exactly 2 results; got {len(result)}: " + repr(result)
    assert result[0][0] == "alpha", "alpha (delta=-3) first; got " + repr(result)
    assert result[1][0] == "beta", "beta (delta=-2) second; got " + repr(result)


def test_n_zero_returns_empty_list() -> None:
    """n=0 -> [] regardless of whether there are shrinking classes.

    Kills impl returning [] only when no shrinkage exists.
    """
    scan_a = [_p("alpha", 0), _p("alpha", 1)]
    scan_b = []
    result = top_shrinking_classes(scan_a, scan_b, n=0)
    assert result == [], "n=0 -> []; got " + repr(result)


def test_tie_break_by_class_name_ascending() -> None:
    """Classes with equal delta sorted by class name ascending.

    Kills impl with wrong tie-break direction.
    alpha delta=-2, zeta delta=-2 -> alpha (smaller name) comes first.
    """
    scan_a = [
        _p("zeta", 0),
        _p("zeta", 1),
        _p("alpha", 0),
        _p("alpha", 1),
    ]
    scan_b = []
    result = top_shrinking_classes(scan_a, scan_b)
    assert len(result) == 2, "Two classes; got " + repr(result)
    assert result[0][0] == "alpha", "alpha < zeta -> first on tie; got " + repr(result[0][0])
    assert result[1][0] == "zeta", "zeta -> second on tie; got " + repr(result[1][0])
