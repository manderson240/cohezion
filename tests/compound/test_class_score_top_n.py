"""Tests for class_score_top_n — item 568.

PRIMARY DISC.: returns LIST of class NAMES (not scores, not dict). Length <= n.
"""
from __future__ import annotations
from cohezion.compound.problem_discovery import class_score_top_n, Problem

W = {"HIGH": 5.0, "MEDIUM": 3.0, "LOW": 1.0}


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_empty_returns_empty_list():
    assert class_score_top_n([], W, 3) == []


def test_returns_names_not_scores_primary_discriminator():
    """PRIMARY DISC.: returns class NAMES not scores.

    A=5.0, B=3.0: top_n(n=2) returns ['A','B'], not [5.0, 3.0] or {'A':5.0}.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "MEDIUM")]
    result = class_score_top_n(problems, W, 2)
    assert result == ["A", "B"]  # names, sorted descending by score


def test_n_limits_length():
    """Returns at most n items."""
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "MEDIUM"), _p("C", "f3", "LOW")]
    result = class_score_top_n(problems, W, 2)
    assert len(result) == 2
    assert result[0] == "A"  # highest score first


def test_n_zero_returns_empty():
    """n=0 returns []."""
    problems = [_p("A", "f1", "HIGH")]
    assert class_score_top_n(problems, W, 0) == []


def test_ties_broken_by_name_lexicographic():
    """Ties broken by name: 'A' before 'B' for equal scores."""
    problems = [_p("B", "f1", "HIGH"), _p("A", "f2", "HIGH")]  # both score 5.0
    result = class_score_top_n(problems, W, 1)
    assert result == ["A"]  # 'A' < 'B' lexicographically
