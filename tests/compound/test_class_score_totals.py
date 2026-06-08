"""Tests for class_score_totals — item 560.

PRIMARY DISC.: returns DICT of per-class totals (not a single float like class_score_sum).
Returns dict[str, float], empty -> {}.
"""

from __future__ import annotations
from cohezion.compound.problem_discovery import class_score_totals, Problem

W = {"HIGH": 5.0, "MEDIUM": 3.0, "LOW": 1.0}


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_empty_returns_empty_dict():
    assert class_score_totals([], W) == {}


def test_dict_not_float_primary_discriminator():
    """PRIMARY DISC.: returns dict, not single float like class_score_sum.

    Two classes: class_score_sum = 8.0 (total); class_score_totals = {'A': 5.0, 'B': 3.0}.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "MEDIUM")]
    result = class_score_totals(problems, W)
    assert isinstance(result, dict)
    assert result == {"A": 5.0, "B": 3.0}  # dict, not 8.0


def test_same_class_accumulates():
    """Multiple problems in same class sum their weights."""
    problems = [_p("A", "f1", "HIGH"), _p("A", "f2", "LOW")]
    result = class_score_totals(problems, W)
    assert result == {"A": 6.0}  # 5.0 + 1.0


def test_unknown_severity_zero():
    """Unknown severity contributes 0.0."""
    result = class_score_totals([_p("A", "f1", "UNKNOWN")], W)
    assert result == {"A": 0.0}


def test_multiple_classes_correct_separation():
    """Each class total is independent; sum of values == class_score_sum."""
    problems = [
        _p("A", "f1", "HIGH"),
        _p("A", "f2", "LOW"),  # A: 6.0
        _p("B", "f3", "MEDIUM"),
        _p("B", "f4", "LOW"),  # B: 4.0
    ]
    result = class_score_totals(problems, W)
    assert result == {"A": 6.0, "B": 4.0}
    assert sum(result.values()) == 10.0  # matches class_score_sum
