"""Item 648: fid_severity_hi_lo_ratio() -- HIGH/LOW severity ratio per fid.

For each fid, count(HIGH) / count(LOW).
Fids with no LOW problems are omitted.  float > 0.0.  Empty -> {}.
Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_hi_lo_ratio


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class; ratio = HIGH/LOW, not HIGH/total.

    fid 'f1': 4 HIGH + 2 LOW -> ratio=2.0.
    Result key must be 'f1', not 'A'.
    Kills class-axis impl and HIGH/total concentration impl.
    """
    problems = [_p("A", "f1", "HIGH")] * 4 + [_p("A", "f1", "LOW")] * 2
    result = fid_severity_hi_lo_ratio(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert abs(result["f1"] - 2.0) < 1e-9, (
        f"4H+2L -> HIGH/LOW=2.0; got {result['f1']} (concentration=4/6≈0.67 wrong)"
    )
    assert isinstance(result["f1"], float), "Must be float"


def test_no_low_fid_omitted() -> None:
    """Fid with no LOW problems is omitted from result."""
    problems = [_p("A", "f2", "HIGH")] * 5
    result = fid_severity_hi_lo_ratio(problems)
    assert "f2" not in result, f"No-LOW fid must be omitted; got {result}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_hi_lo_ratio([]) == {}


def test_equal_high_low_ratio_one() -> None:
    """Equal HIGH and LOW -> ratio=1.0."""
    problems = [_p("A", "f3", "HIGH")] * 4 + [_p("B", "f3", "LOW")] * 4
    result = fid_severity_hi_lo_ratio(problems)
    assert "f3" in result, f"fid 'f3' must be present"
    assert abs(result["f3"] - 1.0) < 1e-9, f"4H+4L -> 1.0; got {result['f3']}"


def test_multiple_fids_no_low_omitted() -> None:
    """Fid 'f4' (has LOW) included; fid 'f5' (no LOW) omitted."""
    problems = (
        [_p("A", "f4", "HIGH")] * 6 + [_p("A", "f4", "LOW")] * 2
        + [_p("B", "f5", "HIGH")] * 3
    )
    result = fid_severity_hi_lo_ratio(problems)
    assert "f4" in result and abs(result["f4"] - 3.0) < 1e-9, (
        f"f4: 6H+2L -> 3.0; got {result.get('f4')}"
    )
    assert "f5" not in result, f"f5 (no LOW) must be omitted; got {result}"
