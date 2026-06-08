"""Tests for fid_score_top_n — item 569.

PRIMARY DISC.: fid-axis complement of class_score_top_n; returns fid NAMES.
"""

from __future__ import annotations
from cohezion.compound.problem_discovery import fid_score_top_n, Problem

W = {"HIGH": 5.0, "MEDIUM": 3.0, "LOW": 1.0}


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_empty_returns_empty_list():
    assert fid_score_top_n([], W, 3) == []


def test_fid_axis_not_class_axis_primary_discriminator():
    """PRIMARY DISC.: one class, 3 fids: class_top_n=['A'], fid_top_n=['f1','f2'] for n=2."""
    problems = [_p("A", "f1", "HIGH"), _p("A", "f2", "MEDIUM"), _p("A", "f3", "LOW")]
    result = fid_score_top_n(problems, W, 2)
    assert result == ["f1", "f2"]  # fid names, not class names


def test_n_limits_length():
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "MEDIUM"), _p("C", "f3", "LOW")]
    assert len(fid_score_top_n(problems, W, 2)) == 2
    assert fid_score_top_n(problems, W, 2)[0] == "f1"


def test_n_zero_returns_empty():
    assert fid_score_top_n([_p("A", "f1", "HIGH")], W, 0) == []


def test_ties_broken_by_fid_name():
    """Ties broken by fid name lexicographically."""
    problems = [_p("A", "f_b", "HIGH"), _p("B", "f_a", "HIGH")]  # both score 5.0
    result = fid_score_top_n(problems, W, 1)
    assert result == ["f_a"]  # 'f_a' < 'f_b'
