"""Item 723: fid_problem_count_by_severity_rank() -- rank histogram per fid.

Fid-axis complement of class_problem_count_by_severity_rank (item 722).
fid_problem_count_by_severity_rank(problems) -> dict[str, dict[int, int]].
All 5 rank keys 0-4 always present.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID, inner int rank keys 0-4;
     fid 'f1': CRITICAL(4)+HIGH(3)+HIGH(3) -> {0:0,1:0,2:0,3:2,4:1};
     class-outer wrong; str-keyed inner wrong.
  2. Empty -> {}.
  3. Multiple fids independent.
  4. All 5 rank keys always present.
  5. Unknown severity -> rank 0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_problem_count_by_severity_rank

_ALL_RANKS = {0, 1, 2, 3, 4}


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_int_rank_histogram_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID, inner keys are INT ranks 0-4.

    fid 'f1': CRITICAL(4)+HIGH(3)+HIGH(3) -> {0:0, 1:0, 2:0, 3:2, 4:1}.
    class-outer wrong (key='A'); str-keyed wrong.
    """
    problems = [_p("f1", "CRITICAL"), _p("f1", "HIGH"), _p("f1", "HIGH")]
    result = fid_problem_count_by_severity_rank(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    inner = result["f1"]
    assert set(inner.keys()) == _ALL_RANKS, (
        f"Must have exactly ranks {{0,1,2,3,4}}; got {set(inner.keys())}"
    )
    assert inner[4] == 1, f"CRITICAL->rank 4: count=1; got {inner.get(4)}"
    assert inner[3] == 2, f"2xHIGH->rank 3: count=2; got {inner.get(3)}"
    assert inner[0] == 0 and inner[1] == 0 and inner[2] == 0


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_problem_count_by_severity_rank([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid has its own histogram."""
    problems = [_p("f2", "CRITICAL"), _p("f2", "LOW")]  # f2: rank4=1, rank1=1
    problems += [_p("f3", "MEDIUM"), _p("f3", "MEDIUM")]  # f3: rank2=2
    result = fid_problem_count_by_severity_rank(problems)
    assert result["f2"][4] == 1 and result["f2"][1] == 1 and result["f2"][2] == 0
    assert result["f3"][2] == 2 and result["f3"][4] == 0 and result["f3"][1] == 0


def test_all_five_ranks_always_present() -> None:
    """Single problem -> 4 ranks have count 0 (all 5 keys present)."""
    problems = [_p("f4", "MEDIUM")]  # rank=2
    inner = fid_problem_count_by_severity_rank(problems)["f4"]
    assert set(inner.keys()) == _ALL_RANKS, f"All 5 rank keys required; got {set(inner.keys())}"
    assert inner[2] == 1 and inner[0] == 0 and inner[4] == 0


def test_unknown_severity_maps_to_rank_zero() -> None:
    """Unknown severity -> rank 0 bucket."""
    problems = [_p("f5", "UNKNOWN"), _p("f5", "INFO")]
    inner = fid_problem_count_by_severity_rank(problems)["f5"]
    assert inner[0] == 2, f"UNKNOWN+INFO both rank=0 -> [0]=2; got {inner.get(0)}"
