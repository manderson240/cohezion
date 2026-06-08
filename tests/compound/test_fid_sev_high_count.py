"""Item 663: fid_sev_high_count() -- raw count of HIGH problems per fid.

FID-axis complement of class_sev_high_count (item 662).
For each fid: count(HIGH).
int >= 0.  fids with 0 HIGH included.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_sev_high_count


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_high_count_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class; raw count of HIGH not rate.

    fid 'f1': 3 HIGH + 2 CRITICAL -> count=3 (not rate=0.6, not class-keyed).
    Key must be 'f1', NOT 'A'. Kills class-axis impl and rate impl.
    """
    problems = [_p("A", "f1", "HIGH")] * 3 + [_p("A", "f1", "CRITICAL")] * 2
    result = fid_sev_high_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 3, (
        f"3 HIGH+2 CRIT -> count=3; got {result['f1']} (rate=0.6 wrong, class-keyed wrong)"
    )
    assert isinstance(result["f1"], int), "Must be int"


def test_zero_high_fid_included() -> None:
    """fid with 0 HIGH -> count=0 (fid present in result)."""
    problems = [_p("A", "f2", "CRITICAL")] * 3
    result = fid_sev_high_count(problems)
    assert "f2" in result
    assert result["f2"] == 0, f"0 HIGH -> count=0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_sev_high_count([]) == {}


def test_all_high_count_equals_total() -> None:
    """All HIGH -> count = total."""
    problems = [_p("A", "f3", "HIGH")] * 8
    result = fid_sev_high_count(problems)
    assert result["f3"] == 8, f"8 HIGH -> count=8; got {result.get('f3')}"


def test_multiple_fids_independent_high_counts() -> None:
    """Multiple fids get independent HIGH counts."""
    problems = [_p("A", "f4", "HIGH")] * 2 + [_p("A", "f4", "LOW")] * 3 + [_p("B", "f5", "LOW")] * 5
    result = fid_sev_high_count(problems)
    assert result["f4"] == 2, f"f4: 2 HIGH -> count=2; got {result.get('f4')}"
    assert result["f5"] == 0, f"f5: 0 HIGH -> count=0; got {result.get('f5')}"
