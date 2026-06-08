"""Item 607: fid_severity_range() -- range of severity counts per fid.

FID-axis complement of class_severity_range.
Returns {fid: max_count - min_count}.  int.  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_range


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid. Same int range formula, fid axis."""
    problems = [_p("A", "f1", "HIGH")] * 5 + [_p("A", "f1", "LOW")]
    result = fid_severity_range(problems)
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {result}"
    assert result["f1"] == 4, f"max=5, min=1 -> range=4; got {result['f1']}"
    assert isinstance(result["f1"], int), (
        "Range must be int; got " + type(result["f1"]).__name__
    )


def test_single_severity_range_zero() -> None:
    """Single severity -> 0."""
    problems = [_p("A", "fy", "CRITICAL")] * 4
    result = fid_severity_range(problems)
    assert result["fy"] == 0, f"Single-severity -> 0; got {result['fy']}"


def test_uniform_range_zero() -> None:
    """Uniform counts -> 0."""
    problems = [_p("A", "fx", "HIGH")] * 3 + [_p("B", "fx", "LOW")] * 3
    result = fid_severity_range(problems)
    assert result["fx"] == 0, f"Uniform [3,3] -> range=0; got {result['fx']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_range([]) == {}


def test_three_severity_range() -> None:
    """HIGH=5, MED=2, LOW=1 -> range=4."""
    problems = (
        [_p("A", "fz", "HIGH")] * 5
        + [_p("B", "fz", "MEDIUM")] * 2
        + [_p("C", "fz", "LOW")]
    )
    result = fid_severity_range(problems)
    assert result["fz"] == 4, f"max=5, min=1 -> range=4; got {result['fz']}"
