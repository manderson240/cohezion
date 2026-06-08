"""Item 519: fids_tied_at_score() -- frozenset of finding IDs at exact target score (2026-06-08).

``fids_tied_at_score(problems, weights, target_score) -> frozenset[str]``:
Returns frozenset of finding_ids whose total weighted severity score equals
exactly ``target_score`` (float equality).  Empty input → frozenset().
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns frozenset of FID names (not class names).
     Kills impl reusing classes_tied_at_score on the wrong axis.
  2. Empty input -> frozenset() (not raise, not None).
     Kills impl calling aggregation on empty without guard.
  3. No fid at target -> frozenset() (not raise, not None).
     Kills impl returning all fids when nothing matches.
  4. Multiple fids tied at target -> all included in frozenset.
     Kills impl returning only first match.
  5. Multi-record fid accumulation before equality check.
     Kills impl comparing individual record weights to target (not accumulated totals).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fids_tied_at_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_frozenset_of_fids_not_classes() -> None:
    """PRIMARY DISC.: returns frozenset of fid names, not class names.

    ClassA fid1=5.0, ClassA fid2=1.0; target=5.0 -> {fid1} not {ClassA}.
    Kills impl reusing classes_tied_at_score on wrong axis.
    """
    problems = [
        _p("ClassA", "fid1", "HIGH"),   # fid1: 5.0
        _p("ClassA", "fid2", "LOW"),    # fid2: 1.0
    ]
    result = fids_tied_at_score(problems, {"HIGH": 5.0, "LOW": 1.0}, 5.0)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert result == frozenset({"fid1"}), "fid1 scored 5.0 == target 5.0; got " + repr(result)
    assert "ClassA" not in result, "Must not contain class names"


def test_empty_input_returns_frozenset() -> None:
    """Empty input -> frozenset() (not raise, not None).

    Kills impl calling any aggregation on empty sequence without guard.
    """
    result = fids_tied_at_score([], {"HIGH": 3.0}, 3.0)
    assert isinstance(result, frozenset), "Empty -> frozenset; got " + repr(type(result))
    assert result == frozenset(), "Empty input -> empty frozenset; got " + repr(result)


def test_no_match_returns_empty_frozenset() -> None:
    """No fid at target score -> frozenset() (not raise, not None).

    fid1=5.0, fid2=1.0; target=3.0 -> frozenset().
    Kills impl returning all fids or the closest fid.
    """
    problems = [
        _p("ClassA", "fid1", "HIGH"),   # 5.0
        _p("ClassA", "fid2", "LOW"),    # 1.0
    ]
    result = fids_tied_at_score(problems, {"HIGH": 5.0, "LOW": 1.0}, 3.0)
    assert result == frozenset(), "No fid at 3.0 -> frozenset(); got " + repr(result)


def test_multiple_tied_fids_all_returned() -> None:
    """Multiple fids at same target score -> all included in frozenset.

    fid_a=3.0, fid_b=3.0, fid_c=5.0; target=3.0 -> {fid_a, fid_b}.
    Kills impl returning only first-seen match.
    """
    problems = [
        _p("ClassA", "fid_a", "MED"),    # 3.0
        _p("ClassA", "fid_b", "MED"),    # 3.0
        _p("ClassA", "fid_c", "HIGH"),   # 5.0
    ]
    result = fids_tied_at_score(problems, {"HIGH": 5.0, "MED": 3.0}, 3.0)
    assert result == frozenset({"fid_a", "fid_b"}), (
        "fid_a and fid_b both at 3.0; got " + repr(result)
    )
    assert "fid_c" not in result, "fid_c=5.0 must not appear"


def test_multi_record_accumulation_before_comparison() -> None:
    """Fid total accumulates across records before equality check.

    fid_x: LOW(1.0)+LOW(1.0)=2.0; fid_y: MED(2.0)=2.0; fid_z: HIGH(3.0)=3.0.
    target=2.0 -> {fid_x, fid_y}.
    Kills impl comparing individual record weights to target instead of accumulated totals.
    """
    problems = [
        _p("ClassA", "fid_x", "LOW"),    # +1.0
        _p("ClassA", "fid_x", "LOW"),    # +1.0 -> total 2.0
        _p("ClassB", "fid_y", "MED"),    # 2.0
        _p("ClassC", "fid_z", "HIGH"),   # 3.0
    ]
    result = fids_tied_at_score(problems, {"HIGH": 3.0, "MED": 2.0, "LOW": 1.0}, 2.0)
    assert result == frozenset({"fid_x", "fid_y"}), (
        "fid_x=2.0 and fid_y=2.0 match; fid_z=3.0 excluded; got " + repr(result)
    )
    assert "fid_z" not in result, "fid_z=3.0 != 2.0; must not appear"
