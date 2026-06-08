"""Item 729: fid_severity_rank_median() -- median severity rank per fid.

Fid-axis complement of class_severity_rank_median (item 728).
fid_severity_rank_median(problems) -> dict[str, float].
Median rank; float.  Single-problem -> that rank.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; skewed: CRITICAL×2+INFO -> median=4.0; mean=2.67 wrong;
     class-outer wrong.
  2. Even count averages two middle.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_median


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_median_not_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND median (not mean).

    fid 'f1': CRITICAL(4)×2+INFO(0) -> sorted=[0,4,4]; median=4.0; mean=2.67 wrong.
    class-outer wrong (key='A').
    """
    problems = [_p("f1", "CRITICAL"), _p("f1", "CRITICAL"), _p("f1", "INFO")]
    result = fid_severity_rank_median(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    assert abs(result["f1"] - 4.0) < 1e-9, (
        f"sorted=[0,4,4] -> median=4.0; mean=2.67 wrong; got {result['f1']}"
    )
    assert isinstance(result["f1"], float), f"Must be float; got {type(result['f1'])}"


def test_even_count_averages_two_middle() -> None:
    """Even count: avg two middle; LOW(1)+MEDIUM(2)+HIGH(3)+CRITICAL(4) -> 2.5."""
    problems = [_p("f2", "LOW"), _p("f2", "MEDIUM"), _p("f2", "HIGH"), _p("f2", "CRITICAL")]
    result = fid_severity_rank_median(problems)
    assert abs(result["f2"] - 2.5) < 1e-9, f"sorted=[1,2,3,4] -> 2.5; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_median([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid computed independently."""
    problems = [_p("f3", "HIGH")] * 3  # f3: all rank 3 -> median=3.0
    problems += [_p("f4", "INFO"), _p("f4", "CRITICAL")]  # f4: sorted=[0,4] -> 2.0
    result = fid_severity_rank_median(problems)
    assert abs(result["f3"] - 3.0) < 1e-9, f"f3 uniform HIGH -> 3.0; got {result.get('f3')}"
    assert abs(result["f4"] - 2.0) < 1e-9, f"f4 INFO+CRITICAL -> 2.0; got {result.get('f4')}"


def test_single_problem_gives_float() -> None:
    """Single problem -> float rank."""
    problems = [_p("f5", "MEDIUM")]  # rank=2
    result = fid_severity_rank_median(problems)
    assert result["f5"] == 2.0, f"Single MEDIUM -> 2.0; got {result.get('f5')}"
    assert isinstance(result["f5"], float)
