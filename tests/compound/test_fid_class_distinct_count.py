"""Item 618: fid_class_distinct_count() -- distinct classes per fid.

FID-axis complement of class_fid_distinct_count (item 617).
Returns {fid: distinct_class_count}.  int.  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_class_distinct_count


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_fid_axis_distinct_classes_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid, counts DISTINCT classes.

    fid 'f1': classes A, A, B -> result['f1']==2 (distinct), not result['A']==2.
    Kills impl reusing class_fid_distinct_count on wrong axis.
    """
    problems = [_p("A", "f1"), _p("A", "f1"), _p("B", "f1")]
    result = fid_class_distinct_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 2, f"classes A,A,B for fid 'f1' -> 2 distinct; got {result['f1']}"
    assert isinstance(result["f1"], int), "Must be int; got " + type(result["f1"]).__name__


def test_single_class_returns_one() -> None:
    """All problems in same class -> distinct_count=1."""
    problems = [_p("A", "f1")] * 4
    result = fid_class_distinct_count(problems)
    assert result["f1"] == 1, f"4 problems all class 'A' -> distinct=1; got {result['f1']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_class_distinct_count([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid counts its own distinct classes independently."""
    problems = [
        _p("A", "f1"), _p("B", "f1"), _p("C", "f1"),
        _p("A", "f2"), _p("B", "f2"),
    ]
    result = fid_class_distinct_count(problems)
    assert result["f1"] == 3, f"f1: A,B,C -> 3 distinct; got {result['f1']}"
    assert result["f2"] == 2, f"f2: A,B -> 2 distinct; got {result['f2']}"


def test_same_class_across_fids_counted_independently() -> None:
    """Same class in multiple fids counted per-fid."""
    problems = [_p("A", "f1"), _p("A", "f2")]
    result = fid_class_distinct_count(problems)
    assert result["f1"] == 1, f"f1: class A only -> 1; got {result['f1']}"
    assert result["f2"] == 1, f"f2: class A only -> 1; got {result['f2']}"
