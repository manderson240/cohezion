"""Item 699: fid_severity_rank_max() -- max severity rank per fid (int).

Fid-axis complement of class_severity_rank_max (698).
fid_severity_rank_max(problems) -> dict[str, int].
CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1, INFO=0.  Unknown=0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: key is FID; value is int max rank;
     fid 'f1': INFO(0)+CRITICAL(4) -> max_rank=4;
     class-outer wrong (key is class); label-impl gives 'CRITICAL' (str, wrong type).
  2. Single INFO -> max_rank = 0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Unknown severity gets 0; dominated by known.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_max


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_int_max_primary_discriminator() -> None:
    """PRIMARY DISC.: key is FID, value is int max rank.

    fid 'f1': INFO(0)+CRITICAL(4) -> max_rank=4.
    class-outer gives key='A' wrong; label-impl gives 'CRITICAL' str wrong type.
    """
    problems = [_p("f1", "INFO"), _p("f1", "CRITICAL")]
    result = fid_severity_rank_max(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    got = result["f1"]
    assert got == 4, f"CRITICAL=4 is max; got {got!r} (label 'CRITICAL' wrong type)"
    assert isinstance(got, int), f"Must be int; got {type(got)}"


def test_single_info_gives_zero() -> None:
    """Single INFO -> max_rank = 0."""
    problems = [_p("f2", "INFO")]
    result = fid_severity_rank_max(problems)
    assert result["f2"] == 0, f"INFO=0; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_max([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid uses its own max."""
    problems = [_p("f3", "LOW"), _p("f3", "MEDIUM")]  # max=2
    problems += [_p("f4", "CRITICAL"), _p("f4", "INFO")]  # max=4
    result = fid_severity_rank_max(problems)
    assert result["f3"] == 2, f"f3: MEDIUM=2 is max; got {result.get('f3')}"
    assert result["f4"] == 4, f"f4: CRITICAL=4 is max; got {result.get('f4')}"


def test_unknown_severity_zero_loses_to_known() -> None:
    """Unknown gets 0; any known severity wins."""
    problems = [_p("f5", "UNKNOWN_SEV"), _p("f5", "LOW")]
    result = fid_severity_rank_max(problems)
    assert result["f5"] == 1, f"LOW(1) > UNKNOWN(0); max=1; got {result.get('f5')}"
