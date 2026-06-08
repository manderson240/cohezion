"""Item 605: fid_severity_variance() -- variance of severity counts per fid.

FID-axis complement of class_severity_variance.
Returns {fid: population_variance_of_per_severity_counts}.
Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_variance


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid, NOT class. Same variance formula, fid axis."""
    problems = [_p("A", "f1", "HIGH")] * 4 + [_p("A", "f1", "LOW")]
    result = fid_severity_variance(problems)
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {result}"
    assert abs(result["f1"] - 2.25) < 1e-9, (
        f"counts=[4,1] -> var=2.25; got {result['f1']}"
    )


def test_uniform_distribution_zero_variance() -> None:
    """Uniform counts -> variance=0.0."""
    problems = [_p("A", "fx", "HIGH")] * 3 + [_p("B", "fx", "LOW")] * 3
    result = fid_severity_variance(problems)
    assert abs(result["fx"]) < 1e-9, f"Uniform [3,3] -> var=0.0; got {result['fx']}"


def test_single_severity_zero_variance() -> None:
    """Single severity per fid -> variance=0.0."""
    problems = [_p("A", "fy", "HIGH")] * 5
    result = fid_severity_variance(problems)
    assert abs(result["fy"]) < 1e-9, f"Single-severity -> var=0.0; got {result['fy']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_variance([]) == {}


def test_three_severity_variance() -> None:
    """counts=[3,2,1], mean=2, var=2/3."""
    problems = (
        [_p("A", "fz", "HIGH")] * 3
        + [_p("B", "fz", "MEDIUM")] * 2
        + [_p("C", "fz", "LOW")]
    )
    result = fid_severity_variance(problems)
    expected = 2.0 / 3.0
    assert abs(result["fz"] - expected) < 1e-9, (
        f"counts=[3,2,1] -> var=2/3={expected:.6f}; got {result['fz']}"
    )
