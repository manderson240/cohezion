"""Tests for class_score_fractions — item 564.

PRIMARY DISC.: weighted fraction (not problem count fraction).
Values sum to 1.0. Returns dict[str, float].
"""

from __future__ import annotations
from cohezion.compound.problem_discovery import class_score_fractions, Problem

W = {"HIGH": 5.0, "MEDIUM": 3.0, "LOW": 1.0}


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_empty_returns_empty_dict():
    assert class_score_fractions([], W) == {}


def test_weighted_not_count_primary_discriminator():
    """PRIMARY DISC.: A has [HIGH=5, LOW=1]=6; B has [LOW=1]=1; A fraction=6/7 not 2/3.

    class_problem_fractions would give A=2/3=0.667 (count fraction).
    class_score_fractions gives A=6/7=0.857 (weighted fraction).
    """
    problems = [_p("A", "f1", "HIGH"), _p("A", "f2", "LOW"), _p("B", "f3", "LOW")]
    result = class_score_fractions(problems, W)
    assert abs(result["A"] - 6 / 7) < 1e-9
    assert abs(result["B"] - 1 / 7) < 1e-9


def test_values_sum_to_one():
    """All fractions sum to 1.0."""
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "MEDIUM"), _p("C", "f3", "LOW")]
    result = class_score_fractions(problems, W)
    assert abs(sum(result.values()) - 1.0) < 1e-9


def test_all_zero_weights_returns_zero_fractions():
    """If all severities unknown -> grand_total=0.0 -> all fractions=0.0."""
    problems = [_p("A", "f1", "UNKNOWN"), _p("B", "f2", "UNKNOWN")]
    result = class_score_fractions(problems, W)
    assert all(v == 0.0 for v in result.values())


def test_single_class_fraction_is_one():
    """Single class gets all weight -> fraction 1.0."""
    result = class_score_fractions([_p("A", "f1", "HIGH"), _p("A", "f2", "LOW")], W)
    assert result == {"A": 1.0}
