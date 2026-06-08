"""Item 415: top_n_classes() — top N classes by record count as (name, count) tuples (2026-06-08).

``top_n_classes(problems, n) -> list[tuple[str, int]]``:
Returns list of (class_name, count) tuples for the N highest-count classes.
Sorted descending by count, ascending name tie-break.
n <= 0 or empty -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns list of (str, int) TUPLES not plain class names.
     Kills impl reusing top_n_classes_by_count.
  2. Sorted descending by count.
     Kills impl sorted ascending.
  3. Tie-break ascending by name.
     Kills impl with arbitrary tie-breaking.
  4. n=0 or n<0 returns [].
     Kills impl raising on n<=0.
  5. n > distinct classes returns all classes.
     Kills impl raising on n > len(classes).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_n_classes,
)


def _p(cls: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_list_of_name_count_tuples() -> None:
    """Returns list[(str, int)] not list[str].

    PRIMARY DISCRIMINATOR: kills impl reusing top_n_classes_by_count.
    """
    problems = [_p("alpha"), _p("alpha"), _p("beta")]
    result = top_n_classes(problems, n=2)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert all(isinstance(item, tuple) and len(item) == 2 for item in result)
    assert all(isinstance(name, str) and isinstance(cnt, int) for name, cnt in result)
    assert result[0] == ("alpha", 2), "alpha has 2 records; got " + repr(result)


def test_sorted_descending_by_count() -> None:
    """Top class (highest count) comes first."""
    problems = [_p("small"), _p("big"), _p("big"), _p("big")]
    result = top_n_classes(problems, n=2)
    assert result[0][0] == "big", "big has highest count; got " + repr(result)
    assert result[0][1] == 3
    assert result[1][0] == "small"
    assert result[1][1] == 1


def test_tie_break_ascending_by_name() -> None:
    """Equal counts: class names sorted ascending."""
    problems = [_p("beta"), _p("beta"), _p("alpha"), _p("alpha")]
    result = top_n_classes(problems, n=2)
    names = [name for name, _ in result]
    assert names == ["alpha", "beta"], "Tie: alpha before beta; got " + repr(names)


def test_n_zero_or_negative_returns_empty() -> None:
    """n <= 0 returns [], not raise."""
    problems = [_p("a"), _p("b")]
    assert top_n_classes(problems, n=0) == []
    assert top_n_classes(problems, n=-1) == []


def test_n_exceeds_classes_returns_all() -> None:
    """n > distinct classes returns all classes (not raise)."""
    problems = [_p("x"), _p("y")]
    result = top_n_classes(problems, n=100)
    assert len(result) == 2, "Only 2 distinct classes; got " + repr(len(result))
