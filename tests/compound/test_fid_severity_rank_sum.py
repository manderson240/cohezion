"""Item 695: fid_severity_rank_sum() -- sum of severity ranks per fid.

Fid-axis complement of class_severity_rank_sum (694).
fid_severity_rank_sum(problems) -> dict[str, int].
CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1, INFO=0.  Unknown=0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID, values are rank sums;
     fid 'f1': CRITICAL(4)+HIGH(3)=7; class-outer gives class as key; count-impl gives 2.
  2. Repeated same severity accumulates (LOW+LOW = 1+1=2).
  3. Empty -> {}.
  4. Multiple fids computed independently.
  5. Unknown severity contributes 0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_sum


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_rank_sum_primary_discriminator() -> None:
    """PRIMARY DISC.: key is FID, value is sum of ranks.

    fid 'f1': CRITICAL(4)+HIGH(3) = 7.
    class-outer impl gives key='A' wrong; count-impl gives 2 wrong.
    """
    problems = [_p("f1", "CRITICAL"), _p("f1", "HIGH")]
    result = fid_severity_rank_sum(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    assert result["f1"] == 7, f"CRITICAL(4)+HIGH(3)=7; got {result['f1']} (count=2 wrong)"
    assert isinstance(result["f1"], int), "Must be int"


def test_repeated_severity_accumulates() -> None:
    """Repeated ranks sum (not de-dup)."""
    problems = [_p("f2", "LOW"), _p("f2", "LOW"), _p("f2", "LOW")]
    result = fid_severity_rank_sum(problems)
    assert result["f2"] == 3, f"LOW(1)×3=3; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_sum([]) == {}


def test_multiple_fids_independent() -> None:
    """Different fids computed independently."""
    problems = (
        [_p("f3", "CRITICAL")]
        + [_p("f3", "MEDIUM")]  # 4+2=6
        + [_p("f4", "INFO")] * 4  # 0×4=0
    )
    result = fid_severity_rank_sum(problems)
    assert result["f3"] == 6, f"f3: CRIT+MED=6; got {result.get('f3')}"
    assert result["f4"] == 0, f"f4: INFO×4=0; got {result.get('f4')}"


def test_unknown_severity_contributes_zero() -> None:
    """Unknown severities contribute 0 to sum."""
    problems = [_p("f5", "BOGUS"), _p("f5", "MEDIUM")]
    result = fid_severity_rank_sum(problems)
    assert result["f5"] == 2, f"BOGUS(0)+MEDIUM(2)=2; got {result.get('f5')}"
