"""Tests for fid_class_count — item 559.

PRIMARY DISC.: keyed on FID axis, counts DISTINCT classes (inverse of class_fid_count).
Returns dict[str, int], unweighted.
"""
from __future__ import annotations
from cohezion.compound.problem_discovery import fid_class_count, Problem


def _p(cls: str, fid: str, sev: str = "LOW") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_empty_returns_empty_dict():
    assert fid_class_count([]) == {}


def test_fid_axis_not_class_axis_primary_discriminator():
    """PRIMARY DISC.: fid_a in [ClassA, ClassA, ClassB] -> distinct classes=2.

    class_fid_count => {'ClassA': 1, 'ClassB': 1} (distinct fids per class)
    fid_class_count => {'fid_a': 2} (distinct classes for fid_a)
    These are NOT inverses in general.
    """
    problems = [
        _p("ClassA", "fid_a"),
        _p("ClassA", "fid_a"),  # dup: still 2 distinct classes (ClassA, ClassB)
        _p("ClassB", "fid_a"),
    ]
    result = fid_class_count(problems)
    assert result == {"fid_a": 2}  # 2 distinct classes, not 3 total problems


def test_single_class_per_fid():
    """Fid only in one class -> 1."""
    result = fid_class_count([_p("A", "f1"), _p("A", "f1")])
    assert result == {"f1": 1}


def test_multiple_fids_independent():
    """Each fid tracks its own distinct class count."""
    problems = [
        _p("A", "f1"), _p("B", "f1"),  # f1 in 2 classes
        _p("C", "f2"),                  # f2 in 1 class
    ]
    result = fid_class_count(problems)
    assert result == {"f1": 2, "f2": 1}


def test_cross_cutting_fid_spans_many_classes():
    """A truly cross-cutting fid appears in many classes."""
    problems = [
        _p("A", "cross"), _p("B", "cross"), _p("C", "cross"),
        _p("A", "local"),  # local only in class A
    ]
    result = fid_class_count(problems)
    assert result["cross"] == 3
    assert result["local"] == 1
