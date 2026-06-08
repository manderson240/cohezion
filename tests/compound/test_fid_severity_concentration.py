"""Item 623: fid_severity_concentration() -- FID-axis complement of class_severity_concentration.

Returns {fid: max_severity_count / total_fid_problems}.
float in (0.0, 1.0].  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_concentration


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid, NOT class.

    fid 'f1': HIGH=3, LOW=1 -> concentration=0.75.
    Result key must be 'f1' (fid), not 'A' (class).
    Kills impl using class axis or calling class_severity_concentration.
    """
    problems = [_p("A", "f1", "HIGH")] * 3 + [_p("A", "f1", "LOW")]
    result = fid_severity_concentration(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert abs(result["f1"] - 0.75) < 1e-9, (
        f"HIGH=3, LOW=1 -> max/total=3/4=0.75; got {result['f1']}"
    )
    assert isinstance(result["f1"], float), "Must be float; got " + type(result["f1"]).__name__


def test_single_severity_returns_one() -> None:
    """Single severity bucket for a fid -> concentration=1.0."""
    problems = [_p("B", "f2", "CRITICAL")] * 5
    result = fid_severity_concentration(problems)
    assert abs(result["f2"] - 1.0) < 1e-9, (
        f"Single severity -> concentration=1.0; got {result['f2']}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_concentration([]) == {}


def test_multiple_fids_independent_concentrations() -> None:
    """Multiple fids each get independent concentration.

    fid 'f1': HIGH=6, LOW=4 -> max=6, total=10 -> 0.6.
    fid 'f2': HIGH=1, LOW=1, MED=1 -> max=1, total=3 -> 1/3.
    """
    problems = (
        [_p("A", "f1", "HIGH")] * 6 + [_p("A", "f1", "LOW")] * 4
        + [_p("B", "f2", "HIGH"), _p("B", "f2", "LOW"), _p("B", "f2", "MED")]
    )
    result = fid_severity_concentration(problems)
    assert abs(result["f1"] - 0.6) < 1e-9, (
        f"f1: HIGH=6, LOW=4 -> 6/10=0.6; got {result['f1']}"
    )
    assert abs(result["f2"] - 1.0 / 3.0) < 1e-9, (
        f"f2: 3 equal severities -> 1/3; got {result['f2']}"
    )


def test_values_in_zero_to_one() -> None:
    """All concentration values in (0, 1]."""
    problems = (
        [_p("A", "f1", "HIGH")] * 5 + [_p("A", "f1", "LOW")] * 3
        + [_p("B", "f2", "CRITICAL")] * 4 + [_p("B", "f2", "LOW")]
    )
    result = fid_severity_concentration(problems)
    for fid, concentration in result.items():
        assert 0.0 < concentration <= 1.0, (
            f"Concentration for {fid} out of (0,1]: {concentration}"
        )
