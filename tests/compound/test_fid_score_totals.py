"""Tests for fid_score_totals — item 561.

PRIMARY DISC.: keyed on FID axis (not class axis). Returns dict[str, float].
"""
from __future__ import annotations
from cohezion.compound.problem_discovery import fid_score_totals, Problem

W = {"HIGH": 5.0, "MEDIUM": 3.0, "LOW": 1.0}


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_empty_returns_empty_dict():
    assert fid_score_totals([], W) == {}


def test_fid_axis_not_class_axis_primary_discriminator():
    """PRIMARY DISC.: single class, multiple fids -> fid has many keys, class has one.

    class_score_totals => {'A': 9.0} (one class key)
    fid_score_totals => {'f1': 5.0, 'f2': 3.0, 'f3': 1.0} (three fid keys)
    """
    problems = [_p("A", "f1", "HIGH"), _p("A", "f2", "MEDIUM"), _p("A", "f3", "LOW")]
    result = fid_score_totals(problems, W)
    assert result == {"f1": 5.0, "f2": 3.0, "f3": 1.0}  # not {'A': 9.0}


def test_same_fid_accumulates():
    """Multiple problems with same fid sum their weights."""
    problems = [_p("A", "f1", "HIGH"), _p("B", "f1", "LOW")]
    result = fid_score_totals(problems, W)
    assert result == {"f1": 6.0}  # 5.0 + 1.0


def test_unknown_severity_zero():
    result = fid_score_totals([_p("A", "f1", "UNKNOWN")], W)
    assert result == {"f1": 0.0}


def test_sum_of_values_equals_fid_score_sum():
    """Sum of dict values matches what fid_score_sum would return."""
    problems = [
        _p("A", "f1", "HIGH"), _p("B", "f1", "LOW"),   # f1: 6.0
        _p("A", "f2", "MEDIUM"),                         # f2: 3.0
    ]
    result = fid_score_totals(problems, W)
    assert result == {"f1": 6.0, "f2": 3.0}
    assert sum(result.values()) == 9.0
