"""Tests for fid_max_severity_weight — item 557.

PRIMARY DISC.: keyed on FID axis (not class axis).
Returns dict[str, float] with max single weight per fid.
"""

from __future__ import annotations
from cohezion.compound.problem_discovery import fid_max_severity_weight, Problem

W = {"HIGH": 5.0, "MEDIUM": 3.0, "LOW": 1.0}


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_empty_returns_empty_dict():
    assert fid_max_severity_weight([], W) == {}


def test_fid_axis_not_class_axis_primary_discriminator():
    """PRIMARY DISC.: single class, multiple fids -> fid max != class max.

    Class A has problems [HIGH, LOW, HIGH] across fids f1, f2, f3.
    class_max_severity_weight => {'A': 5.0} (max across class)
    fid_max_severity_weight => {'f1': 5.0, 'f2': 1.0, 'f3': 5.0} (per fid)
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("A", "f2", "LOW"),
        _p("A", "f3", "HIGH"),
    ]
    result = fid_max_severity_weight(problems, W)
    assert result == {"f1": 5.0, "f2": 1.0, "f3": 5.0}


def test_max_not_total_per_fid():
    """Max single weight, not sum. fid has [HIGH=5, HIGH=5] -> max=5, not total=10."""
    problems = [
        _p("A", "f1", "HIGH"),
        _p("B", "f1", "HIGH"),  # same fid, same sev
    ]
    result = fid_max_severity_weight(problems, W)
    assert result == {"f1": 5.0}  # max=5, not total=10


def test_unknown_severity_gives_zero():
    """0.0 for unknown severity weight (graceful, no KeyError)."""
    problems = [_p("A", "f1", "CRITICAL")]
    result = fid_max_severity_weight(problems, W)
    assert result == {"f1": 0.0}


def test_multiple_fids_independent():
    """Each fid's max is computed independently."""
    problems = [
        _p("A", "f1", "LOW"),  # f1 max starts at 1.0
        _p("A", "f1", "HIGH"),  # f1 max updates to 5.0
        _p("B", "f2", "MEDIUM"),  # f2 max = 3.0
    ]
    result = fid_max_severity_weight(problems, W)
    assert result == {"f1": 5.0, "f2": 3.0}
