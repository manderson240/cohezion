"""Tests for class_score_rank — item 566.

PRIMARY DISC.: returns RANK (1=highest, different from score value); dense ranking for ties.
"""

from __future__ import annotations
from cohezion.compound.problem_discovery import class_score_rank, Problem

W = {"HIGH": 5.0, "MEDIUM": 3.0, "LOW": 1.0}


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_empty_returns_empty_dict():
    assert class_score_rank([], W) == {}


def test_rank_not_score_primary_discriminator():
    """PRIMARY DISC.: rank=1 means highest score; A(5.0)=rank1, B(3.0)=rank2, C(1.0)=rank3."""
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "MEDIUM"), _p("C", "f3", "LOW")]
    result = class_score_rank(problems, W)
    assert result == {"A": 1, "B": 2, "C": 3}
    # A has score 5.0 not rank 5.0 -> rank 1 \!= score 5


def test_ties_get_same_dense_rank():
    """Ties get same rank; next rank is consecutive (dense, not skip).

    A=5.0 (rank 1), B=5.0 (rank 1), C=1.0 (rank 2) -- next rank after tie is 2, not 3.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "HIGH"), _p("C", "f3", "LOW")]
    result = class_score_rank(problems, W)
    assert result["A"] == 1
    assert result["B"] == 1
    assert result["C"] == 2  # dense: rank 2 not 3


def test_single_class_rank_is_one():
    result = class_score_rank([_p("A", "f1", "HIGH")], W)
    assert result == {"A": 1}


def test_lowest_score_gets_highest_rank_number():
    """The lowest scoring class has the largest rank number."""
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "MEDIUM"), _p("C", "f3", "LOW")]
    result = class_score_rank(problems, W)
    assert max(result.values()) == 3  # C is last (lowest score, highest rank number)
