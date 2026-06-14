"""Item 468: dominant_fid_for_severity() -- fid most associated with a severity (2026-06-08).

``dominant_fid_for_severity(problems, severity) -> str | None``:
Returns the finding_id with the most records at the given severity.
Tie-break: alphabetically first.  None when severity absent.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns single fid STR (not list -- kills fids_with_severity).
     HIGH: fid_a×3, fid_b×1 -> dominant='fid_a' (str, not list).
     Kills impl reusing fids_with_severity which returns a list.
  2. Tie-break alphabetical: equal per-fid counts -> alphabetically first fid.
     Kills impl returning last-seen or non-deterministic winner.
  3. Absent severity -> None (not raise).
     Kills impl without absence guard.
  4. Empty input -> None (not raise).
     Kills impl with unguarded access.
  5. Only severity-filtered counts contribute (other severities excluded).
     fid_a: HIGH×1, LOW×5.  fid_b: HIGH×3.
     dominant_fid_for_severity(HIGH) -> 'fid_b' (3 vs 1), not 'fid_a' (6 total).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    dominant_fid_for_severity,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_single_fid_not_list() -> None:
    """PRIMARY DISC.: returns single fid str, not a list of fids.

    HIGH: fid_a×3, fid_b×1.  Dominant = 'fid_a' (str, not ['fid_a', 'fid_b']).
    fids_with_severity returns a list -- wrong here.
    """
    problems = [
        _p("c", "fid_a", "HIGH"),
        _p("c", "fid_a", "HIGH"),
        _p("c", "fid_a", "HIGH"),
        _p("c", "fid_b", "HIGH"),
    ]
    result = dominant_fid_for_severity(problems, "HIGH")
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "fid_a", "fid_a dominant for HIGH (3 vs 1); got " + repr(result)


def test_tie_break_alphabetical() -> None:
    """Equal per-fid counts: tie-break alphabetically first fid."""
    problems = [
        _p("c", "fid_z", "HIGH"),
        _p("c", "fid_a", "HIGH"),
    ]
    result = dominant_fid_for_severity(problems, "HIGH")
    assert result == "fid_a", "Tie 'fid_a' < 'fid_z'; got " + repr(result)


def test_absent_severity_returns_none() -> None:
    """Absent severity -> None (not raise)."""
    problems = [_p("c", "fid_a", "HIGH")]
    result = dominant_fid_for_severity(problems, "NONEXISTENT")
    assert result is None, "Absent severity -> None; got " + repr(result)


def test_empty_input_returns_none() -> None:
    """Empty input -> None."""
    result = dominant_fid_for_severity([], "HIGH")
    assert result is None, "Empty -> None; got " + repr(result)


def test_only_severity_filtered_counts() -> None:
    """Only the matching severity contributes (not all records for the fid).

    fid_a: HIGH×1, LOW×5.  fid_b: HIGH×3.
    dominant_for_HIGH -> 'fid_b' (3 HIGH) not 'fid_a' (6 total).
    """
    problems = [
        _p("c", "fid_a", "HIGH"),
        _p("c", "fid_a", "LOW"),
        _p("c", "fid_a", "LOW"),
        _p("c", "fid_a", "LOW"),
        _p("c", "fid_a", "LOW"),
        _p("c", "fid_a", "LOW"),
        _p("c", "fid_b", "HIGH"),
        _p("c", "fid_b", "HIGH"),
        _p("c", "fid_b", "HIGH"),
    ]
    result = dominant_fid_for_severity(problems, "HIGH")
    assert result == "fid_b", "fid_b has 3 HIGH vs fid_a 1 HIGH; got " + repr(result)
