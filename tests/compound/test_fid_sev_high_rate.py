"""Item 657: fid_sev_high_rate() -- HIGH/total fraction per fid.

FID-axis complement of class_sev_high_rate (item 656).
For each fid: count(HIGH) / total_fid_problems.
float in [0, 1].  0.0 = no HIGH.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_sev_high_rate


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class; rate = HIGH/total not HIGH/LOW.

    fid 'f1': 2 HIGH + 3 LOW -> high_rate=0.4 (not HIGH/LOW=0.67).
    Key must be 'f1', NOT 'A'. Kills class-axis impl and ratio impl.
    """
    problems = [_p("A", "f1", "HIGH")] * 2 + [_p("A", "f1", "LOW")] * 3
    result = fid_sev_high_rate(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert abs(result["f1"] - 0.4) < 1e-9, (
        f"2 HIGH+3 LOW -> HIGH/total=0.4; got {result['f1']} (HIGH/LOW=0.67 wrong)"
    )
    assert isinstance(result["f1"], float), "Must be float"


def test_no_high_rate_zero_fid_present() -> None:
    """No HIGH problems for fid -> rate=0.0 (fid present, rate 0)."""
    problems = [_p("A", "f2", "LOW")] * 3 + [_p("A", "f2", "CRITICAL")]
    result = fid_sev_high_rate(problems)
    assert "f2" in result, f"fid must be present; got {result}"
    assert abs(result["f2"]) < 1e-9, f"No HIGH -> rate=0.0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_sev_high_rate([]) == {}


def test_all_high_rate_one() -> None:
    """All problems HIGH -> rate=1.0."""
    problems = [_p("A", "f3", "HIGH")] * 6
    result = fid_sev_high_rate(problems)
    assert abs(result["f3"] - 1.0) < 1e-9, f"All HIGH -> 1.0; got {result.get('f3')}"


def test_multiple_fids_independent_rates() -> None:
    """Multiple fids each get independent HIGH rates.

    fid 'f4': 3 HIGH + 2 CRITICAL -> high_rate=0.6.
    fid 'f5': 0 HIGH + 4 LOW -> high_rate=0.0.
    """
    problems = (
        [_p("A", "f4", "HIGH")] * 3 + [_p("A", "f4", "CRITICAL")] * 2
        + [_p("B", "f5", "LOW")] * 4
    )
    result = fid_sev_high_rate(problems)
    assert abs(result["f4"] - 0.6) < 1e-9, f"f4: 3/5 -> 0.6; got {result.get('f4')}"
    assert abs(result["f5"]) < 1e-9, f"f5: 0 HIGH -> 0.0; got {result.get('f5')}"
