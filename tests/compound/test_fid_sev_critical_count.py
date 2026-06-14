"""Item 661: fid_sev_critical_count() -- raw count of CRITICAL problems per fid.

FID-axis complement of class_sev_critical_count (item 660).
For each fid: count(CRITICAL).
int >= 0.  fids with 0 CRITICAL included.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_sev_critical_count


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_raw_count_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class; returns RAW COUNT not rate.

    fid 'f1': 2 CRITICAL + 3 HIGH -> count=2 (not rate=0.4, not class-keyed).
    Key must be 'f1', NOT 'A'. Kills class-axis impl and rate impl.
    """
    problems = [_p("A", "f1", "CRITICAL")] * 2 + [_p("A", "f1", "HIGH")] * 3
    result = fid_sev_critical_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 2, f"2 CRIT+3 HIGH -> count=2; got {result['f1']} (rate=0.4 wrong)"
    assert isinstance(result["f1"], int), "Must be int"


def test_zero_critical_fid_included() -> None:
    """fid with 0 CRITICAL -> count=0 (fid still present in result)."""
    problems = [_p("A", "f2", "HIGH")] * 3
    result = fid_sev_critical_count(problems)
    assert "f2" in result, f"fid must be present even with 0 CRITICAL; got {result}"
    assert result["f2"] == 0, f"0 CRITICAL -> count=0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_sev_critical_count([]) == {}


def test_all_critical_count_equals_total() -> None:
    """All problems CRITICAL -> count = len(problems)."""
    problems = [_p("A", "f3", "CRITICAL")] * 7
    result = fid_sev_critical_count(problems)
    assert result["f3"] == 7, f"All CRIT -> count=7; got {result.get('f3')}"


def test_multiple_fids_independent_counts() -> None:
    """Multiple fids each get independent CRITICAL counts.

    fid 'f4': 4 CRITICAL + 1 LOW -> count=4.
    fid 'f5': 0 CRITICAL + 3 HIGH -> count=0.
    """
    problems = (
        [_p("A", "f4", "CRITICAL")] * 4 + [_p("A", "f4", "LOW")] + [_p("B", "f5", "HIGH")] * 3
    )
    result = fid_sev_critical_count(problems)
    assert result["f4"] == 4, f"f4: 4 CRIT -> count=4; got {result.get('f4')}"
    assert result["f5"] == 0, f"f5: 0 CRIT -> count=0; got {result.get('f5')}"
