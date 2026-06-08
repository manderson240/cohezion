"""Item 659: fid_sev_low_rate() -- LOW/total fraction per fid.

FID-axis complement of class_sev_low_rate (item 658).
For each fid: count(LOW) / total_fid_problems.
float in [0, 1].  0.0 = no LOW.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_sev_low_rate


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_low_not_high_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class; rate = LOW/total (NOT HIGH/total).

    fid 'f1': 2 HIGH + 3 LOW -> low_rate=0.6 (not 0.4 HIGH-rate wrong).
    Key must be 'f1', NOT 'A'. Kills class-axis impl and high-rate impl.
    """
    problems = [_p("A", "f1", "HIGH")] * 2 + [_p("A", "f1", "LOW")] * 3
    result = fid_sev_low_rate(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert abs(result["f1"] - 0.6) < 1e-9, (
        f"2 HIGH+3 LOW -> LOW/total=0.6; got {result['f1']} (0.4=high-rate wrong)"
    )
    assert isinstance(result["f1"], float), "Must be float"


def test_no_low_rate_zero_fid_present() -> None:
    """No LOW problems for fid -> rate=0.0 (fid present, rate 0)."""
    problems = [_p("A", "f2", "HIGH")] * 4
    result = fid_sev_low_rate(problems)
    assert "f2" in result, f"fid must be present; got {result}"
    assert abs(result["f2"]) < 1e-9, f"No LOW -> rate=0.0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_sev_low_rate([]) == {}


def test_all_low_rate_one() -> None:
    """All problems LOW -> rate=1.0."""
    problems = [_p("A", "f3", "LOW")] * 5
    result = fid_sev_low_rate(problems)
    assert abs(result["f3"] - 1.0) < 1e-9, f"All LOW -> 1.0; got {result.get('f3')}"


def test_multiple_fids_independent_low_rates() -> None:
    """Multiple fids each get independent LOW rates.

    fid 'f4': 1 LOW + 3 HIGH -> low_rate=0.25.
    fid 'f5': 4 LOW + 0 HIGH -> low_rate=1.0.
    """
    problems = (
        [_p("A", "f4", "LOW")] + [_p("A", "f4", "HIGH")] * 3
        + [_p("B", "f5", "LOW")] * 4
    )
    result = fid_sev_low_rate(problems)
    assert abs(result["f4"] - 0.25) < 1e-9, f"f4: 1/4 LOW -> 0.25; got {result.get('f4')}"
    assert abs(result["f5"] - 1.0) < 1e-9, f"f5: 4/4 LOW -> 1.0; got {result.get('f5')}"
