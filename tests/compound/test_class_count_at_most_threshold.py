"""Item 374: class_count_at_most_threshold() -- class names with count <= n (2026-06-08).

``class_count_at_most_threshold(problems, n) -> frozenset[str]``:
Returns the frozenset of class names whose total problem record count is <= n.
n=0 always returns frozenset() (no class can have count <= 0 in a non-empty list).
Complement invariant: above_threshold(n) | at_most_threshold(n) == all distinct classes.
Empty -> frozenset().  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: uses <= n (at most), not < n.
     Kills impl using strict < threshold.
  2. n=0 returns frozenset() (no class has count <= 0).
     Kills impl returning all classes for n=0.
  3. Complement invariant: above(n) | at_most(n) == all distinct classes.
     Kills impl with overlap or gap.
  4. Empty input returns frozenset().
     Kills impl raising on empty.
  5. Returns frozenset of class name strings, not Problem objects.
     Kills impl returning Problem list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_count_above_threshold,
    class_count_at_most_threshold,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_at_most_is_lte_not_lt() -> None:
    """Returns class names with count <= n, not < n.

    PRIMARY DISCRIMINATOR: kills impl using strict <.
    'alpha' has exactly 2 records; n=2 MUST include it (<=), n=1 must NOT.
    """
    problems = [_p("alpha", "f:0"), _p("alpha", "f:1"), _p("beta", "f:2")]
    result_n2 = class_count_at_most_threshold(problems, 2)
    assert "alpha" in result_n2, "count==2 <= 2: must be included"
    result_n1 = class_count_at_most_threshold(problems, 1)
    assert "alpha" not in result_n1, "count==2 > 1: must NOT be included"
    assert "beta" in result_n1, "count==1 <= 1: must be included"


def test_n_zero_returns_empty() -> None:
    """n=0 returns frozenset() (no class has count <= 0).

    Kills impl returning all classes for n=0.
    """
    problems = [_p("a", "f:0"), _p("b", "f:1")]
    result = class_count_at_most_threshold(problems, 0)
    assert result == frozenset(), "n=0 -> empty"


def test_complement_invariant() -> None:
    """above_threshold(n) | at_most_threshold(n) == all distinct classes.

    Kills impl with overlap or gap.
    """
    problems = [
        _p("a", "f:0"),
        _p("a", "f:1"),
        _p("a", "f:2"),
        _p("b", "f:3"),
        _p("b", "f:4"),
        _p("c", "f:5"),
    ]
    all_classes = frozenset(p.problem_class for p in problems)
    for n in (0, 1, 2, 3, 4):
        above = class_count_above_threshold(problems, n)
        at_most = class_count_at_most_threshold(problems, n)
        assert above | at_most == all_classes, f"n={n}: union must equal all classes"
        assert above & at_most == frozenset(), f"n={n}: must be disjoint"


def test_empty_returns_frozenset() -> None:
    """Empty input returns frozenset() without raising."""
    assert class_count_at_most_threshold([], 0) == frozenset()
    assert class_count_at_most_threshold([], 5) == frozenset()


def test_returns_frozenset_of_class_strings() -> None:
    """Returns frozenset of class name strings, not Problem objects."""
    problems = [_p("x", "f:0"), _p("y", "f:1"), _p("y", "f:2")]
    result = class_count_at_most_threshold(problems, 1)
    assert isinstance(result, frozenset), "Must return frozenset"
    assert result == frozenset({"x"}), "Only x has count <= 1"
