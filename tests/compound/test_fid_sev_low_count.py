"""Item 665: fid_sev_low_count() -- raw count of LOW problems per fid.

FID-axis complement of class_sev_low_count (item 664).
For each fid: count(LOW).
int >= 0.  fids with 0 LOW included.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_sev_low_count


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_low_count_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class; raw count of LOW not rate.

    fid 'f1': 2 LOW + 4 HIGH -> count=2 (not rate=0.33, not class-keyed).
    Kills class-axis impl and rate impl.
    """
    problems = [_p("A", "f1", "LOW")] * 2 + [_p("A", "f1", "HIGH")] * 4
    result = fid_sev_low_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 2, (
        f"2 LOW+4 HIGH -> count=2; got {result['f1']} (rate=0.33 wrong, class-keyed wrong)"
    )
    assert isinstance(result["f1"], int), "Must be int"


def test_zero_low_fid_included() -> None:
    """fid with 0 LOW -> count=0 (fid present in result)."""
    problems = [_p("A", "f2", "HIGH")] * 5
    result = fid_sev_low_count(problems)
    assert "f2" in result
    assert result["f2"] == 0, f"0 LOW -> count=0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_sev_low_count([]) == {}


def test_all_low_count_equals_total() -> None:
    """All LOW -> count = total."""
    problems = [_p("A", "f3", "LOW")] * 9
    result = fid_sev_low_count(problems)
    assert result["f3"] == 9, f"9 LOW -> count=9; got {result.get('f3')}"


def test_multiple_fids_independent_low_counts() -> None:
    """Multiple fids get independent LOW counts."""
    problems = [_p("A", "f4", "LOW")] * 3 + [_p("A", "f4", "HIGH")] + [_p("B", "f5", "CRITICAL")] * 4
    result = fid_sev_low_count(problems)
    assert result["f4"] == 3, f"f4: 3 LOW -> count=3; got {result.get('f4')}"
    assert result["f5"] == 0, f"f5: 0 LOW -> count=0; got {result.get('f5')}"
