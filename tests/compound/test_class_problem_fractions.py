"""Tests for class_problem_fractions — item 562.

PRIMARY DISC.: returns DICT of fractions for ALL classes (not single float like class_problem_fraction).
Values sum to 1.0. Unweighted.
"""

from __future__ import annotations
from cohezion.compound.problem_discovery import class_problem_fractions, Problem


def _p(cls: str, fid: str = "f1", sev: str = "LOW") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_empty_returns_empty_dict():
    assert class_problem_fractions([]) == {}


def test_dict_not_float_primary_discriminator():
    """PRIMARY DISC.: returns dict for all classes, not float for one class.

    class_problem_fraction(problems, 'A') returns 0.6 (single float).
    class_problem_fractions(problems) returns {'A': 0.6, 'B': 0.4} (dict).
    """
    problems = [_p("A"), _p("A"), _p("A"), _p("B"), _p("B")]
    result = class_problem_fractions(problems)
    assert isinstance(result, dict)
    assert result == {"A": 0.6, "B": 0.4}


def test_values_sum_to_one():
    """All fractions sum to 1.0 (partition of unity)."""
    problems = [_p("A"), _p("A"), _p("B"), _p("C")]
    result = class_problem_fractions(problems)
    assert abs(sum(result.values()) - 1.0) < 1e-9


def test_single_class_fraction_is_one():
    """Single class has all problems -> fraction 1.0."""
    result = class_problem_fractions([_p("A"), _p("A")])
    assert result == {"A": 1.0}


def test_equal_classes_equal_fractions():
    """Equal problem counts -> equal fractions."""
    problems = [_p("A"), _p("B"), _p("C"), _p("D")]
    result = class_problem_fractions(problems)
    assert all(abs(v - 0.25) < 1e-9 for v in result.values())
