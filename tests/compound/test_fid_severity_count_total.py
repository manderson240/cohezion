"""Item 614: fid_severity_count_total() -- total problem count per fid.

FID-axis complement of class_severity_count_total (item 613).
Returns {fid: total_count}.  int.  Counts ALL problems regardless of severity.
Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_count_total


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid (not class).

    fid 'f1' with HIGH=3, LOW=2 -> result['f1']==5 (total on fid axis).
    class_severity_count_total would key on problem_class.
    Kills impl reusing class_severity_count_total on wrong axis.
    """
    problems = [_p("A", "f1", "HIGH")] * 3 + [_p("B", "f1", "LOW")] * 2
    result = fid_severity_count_total(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 5, f"3 HIGH + 2 LOW for fid 'f1' = total 5; got {result['f1']}"
    assert isinstance(result["f1"], int), "Must be int; got " + type(result["f1"]).__name__


def test_single_fid_single_severity() -> None:
    """Single fid, single severity -> its total count."""
    problems = [_p("A", "f1", "CRITICAL")] * 6
    result = fid_severity_count_total(problems)
    assert result["f1"] == 6, f"6 problems for fid 'f1' -> total=6; got {result['f1']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_count_total([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids each get independent total counts."""
    problems = [_p("A", "f1", "HIGH")] * 3 + [_p("B", "f2", "LOW")] * 4
    result = fid_severity_count_total(problems)
    assert result["f1"] == 3, f"f1: 3 problems; got {result['f1']}"
    assert result["f2"] == 4, f"f2: 4 problems; got {result['f2']}"


def test_unlabelled_problems_counted() -> None:
    """Unlabelled problems counted in total (all problems regardless of severity)."""
    problems = [_p("A", "f1", "HIGH")] * 2 + [_p("A", "f1", "")]  # 2 + 1 unlabelled
    result = fid_severity_count_total(problems)
    assert result["f1"] == 3, f"2 HIGH + 1 unlabelled = total 3; got {result['f1']}"
