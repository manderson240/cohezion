"""Tests for fid_score_fractions — item 565.

PRIMARY DISC.: fid-axis weighted fraction (one class, 3 fids -> class=1.0, fid=[5/9, 3/9, 1/9]).
"""
from __future__ import annotations
from cohezion.compound.problem_discovery import fid_score_fractions, Problem

W = {"HIGH": 5.0, "MEDIUM": 3.0, "LOW": 1.0}


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_empty_returns_empty_dict():
    assert fid_score_fractions([], W) == {}


def test_fid_axis_not_class_axis_primary_discriminator():
    """PRIMARY DISC.: one class, fids [HIGH=5, MED=3, LOW=1]. class fraction=1.0, fid fractions differ.

    class_score_fractions => {'A': 1.0}
    fid_score_fractions => {'f1': 5/9, 'f2': 3/9, 'f3': 1/9}
    """
    problems = [_p("A", "f1", "HIGH"), _p("A", "f2", "MEDIUM"), _p("A", "f3", "LOW")]
    result = fid_score_fractions(problems, W)
    assert abs(result["f1"] - 5/9) < 1e-9
    assert abs(result["f2"] - 3/9) < 1e-9
    assert abs(result["f3"] - 1/9) < 1e-9


def test_values_sum_to_one():
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "MEDIUM"), _p("C", "f3", "LOW")]
    result = fid_score_fractions(problems, W)
    assert abs(sum(result.values()) - 1.0) < 1e-9


def test_all_zero_weights_returns_zero_fractions():
    problems = [_p("A", "f1", "UNKNOWN"), _p("B", "f2", "UNKNOWN")]
    result = fid_score_fractions(problems, W)
    assert all(v == 0.0 for v in result.values())


def test_single_fid_fraction_is_one():
    result = fid_score_fractions([_p("A", "f1", "HIGH"), _p("B", "f1", "LOW")], W)
    assert result == {"f1": 1.0}
