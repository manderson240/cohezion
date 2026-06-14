"""Tests for class_fid_count — item 558.

PRIMARY DISC.: counts DISTINCT fids per class (not total problems).
Returns dict[str, int], unweighted.
"""

from __future__ import annotations
from cohezion.compound.problem_discovery import class_fid_count, Problem


def _p(cls: str, fid: str, sev: str = "LOW") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_empty_returns_empty_dict():
    assert class_fid_count([]) == {}


def test_distinct_not_total_primary_discriminator():
    """PRIMARY DISC.: class A has [fid1, fid1, fid2] -> distinct=2, total=3.

    class_problem_count returns {'A': 3}; class_fid_count returns {'A': 2}.
    """
    problems = [_p("A", "fid1"), _p("A", "fid1"), _p("A", "fid2")]
    result = class_fid_count(problems)
    assert result == {"A": 2}  # 2 distinct, not 3 total


def test_single_fid_per_class():
    """Single fid in class -> 1."""
    result = class_fid_count([_p("A", "f1"), _p("A", "f1")])
    assert result == {"A": 1}


def test_multiple_classes_independent():
    """Each class tracks its own distinct fids."""
    problems = [
        _p("A", "f1"),
        _p("A", "f2"),
        _p("A", "f1"),  # A: 2 distinct
        _p("B", "f3"),  # B: 1 distinct
    ]
    result = class_fid_count(problems)
    assert result == {"A": 2, "B": 1}


def test_fid_shared_across_classes_counted_per_class():
    """Same fid in two classes counts separately for each class."""
    problems = [
        _p("A", "shared_fid"),
        _p("B", "shared_fid"),
    ]
    result = class_fid_count(problems)
    assert result == {"A": 1, "B": 1}
