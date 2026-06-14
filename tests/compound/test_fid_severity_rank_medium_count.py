"""Item 807: fid_severity_rank_medium_count() -- count rank==2 (MEDIUM only) per fid.

fid_severity_rank_medium_count(problems) -> dict[str, int].
Fid-axis complement of class_severity_rank_medium_count (item 806).
count = count(rank == 2) per fid.  Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [MED*3,HIGH*2] -> 3; class-outer wrong; high_count=2 wrong.
  2. HIGH-only fid -> 0 (fid still present).
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_medium_count


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_outer_medium_count_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key=FID; fid f1: [MED*3,HIGH*2] -> 3; class-outer wrong."""
    problems = (
        [_p("A", "f1", "MEDIUM")] * 3 + [_p("A", "f1", "HIGH")] * 2 + [_p("B", "f2", "MEDIUM")] * 1
    )
    result = fid_severity_rank_medium_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be key; got {list(result)}"
    assert "A" not in result, "Must be keyed by FID not class"
    assert result["f1"] == 3, f"fid f1: MED*3,HIGH*2 -> medium_count=3; got {result['f1']}"
    assert result["f2"] == 1, f"fid f2: MED*1 -> 1; got {result['f2']}"


def test_high_only_gives_zero_not_excluded() -> None:
    """HIGH-only fid -> count=0 (fid still present)."""
    problems = [_p("B", "f3", "HIGH")] * 4
    result = fid_severity_rank_medium_count(problems)
    assert "f3" in result, "Fid f3 must appear with count=0"
    assert result["f3"] == 0, f"No MEDIUM -> 0; got {result['f3']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_medium_count([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids are counted independently."""
    problems = (
        [_p("X", "f10", "MEDIUM")] * 4
        + [_p("X", "f11", "HIGH")] * 3
        + [_p("Y", "f12", "MEDIUM")] * 2
    )
    result = fid_severity_rank_medium_count(problems)
    assert result.get("f10") == 4, f"f10 -> 4; got {result.get('f10')}"
    assert result.get("f11") == 0, f"f11 -> 0 (HIGH not MEDIUM); got {result.get('f11')}"
    assert result.get("f12") == 2, f"f12 -> 2; got {result.get('f12')}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("D", "f99", "MEDIUM"), _p("D", "f99", "HIGH")]
    result = fid_severity_rank_medium_count(problems)
    assert isinstance(result["f99"], int), f"Must be int; got {type(result['f99'])}"
