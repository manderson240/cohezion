"""Item 383: top_n_classes_by_count() -- top N classes by record count (2026-06-08).

``top_n_classes_by_count(problems, n) -> list[str]``:
Returns a list of at most n class names sorted descending by total problem count.
Ties broken by class name ascending (lexicographic).
n=0 -> [].  Empty problems -> [].  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: descending by count, not ascending or random.
     Kills impl that sorts ascending.
  2. Ties broken lexicographically ascending.
     Kills impl with non-deterministic or reverse tie-breaking.
  3. Returns at most n entries even when more classes exist.
     Kills impl returning all classes.
  4. n=0 returns [].
     Kills impl returning all or raising on 0.
  5. Returns class name STRINGS, not Problem objects.
     Kills impl returning [p.problem_class for p in ...] with duplicates.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_n_classes_by_count,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_descending_by_count_not_ascending() -> None:
    """Result is sorted descending by count.

    PRIMARY DISCRIMINATOR: kills impl that sorts ascending.
    alpha=3, beta=2, gamma=1 -> [alpha, beta, gamma].
    """
    problems = [
        _p("alpha", "f:0"),
        _p("alpha", "f:1"),
        _p("alpha", "f:2"),
        _p("beta", "f:3"),
        _p("beta", "f:4"),
        _p("gamma", "f:5"),
    ]
    result = top_n_classes_by_count(problems, 3)
    assert result == ["alpha", "beta", "gamma"], "Descending order alpha>beta>gamma; got " + repr(
        result
    )


def test_ties_broken_lexicographically_ascending() -> None:
    """Ties broken by class name ascending (a < b < c).

    Kills impl with non-deterministic or reverse tie-breaking.
    a=2, b=2, c=1 -> first two are a, b (tied at 2, alpha-asc).
    """
    problems = [
        _p("b", "f:0"),
        _p("b", "f:1"),
        _p("a", "f:2"),
        _p("a", "f:3"),
        _p("c", "f:4"),
    ]
    result = top_n_classes_by_count(problems, 3)
    assert result[0] == "a" or result[1] == "a", "a must be in top 2 (tied at 2)"
    assert result[0] == "b" or result[1] == "b", "b must be in top 2 (tied at 2)"
    assert result[2] == "c", "c (count=1) is last"
    assert result[0] < result[1], "tied classes sorted asc: a before b; got " + repr(result[:2])


def test_returns_at_most_n_entries() -> None:
    """Returns at most n entries even if more classes exist.

    Kills impl returning all classes.
    """
    problems = [_p(f"cls{i}", f"f:{i}") for i in range(10)]
    result = top_n_classes_by_count(problems, 3)
    assert len(result) == 3, "n=3 -> at most 3 results; got " + repr(len(result))
    assert all(isinstance(c, str) for c in result), "Must return strings"


def test_n_zero_returns_empty() -> None:
    """n=0 returns [] without raising."""
    problems = [_p("a", "f:0"), _p("b", "f:1")]
    assert top_n_classes_by_count(problems, 0) == []


def test_empty_problems_returns_empty() -> None:
    """Empty problems list returns [] regardless of n."""
    assert top_n_classes_by_count([], 5) == []
