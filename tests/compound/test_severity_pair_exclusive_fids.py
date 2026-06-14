"""Item 445: severity_pair_exclusive_fids() -- fids in severity_a but not severity_b (2026-06-08).

``severity_pair_exclusive_fids(problems, severity_a, severity_b) -> frozenset[str]``:
Returns frozenset of finding_ids that appear in severity_a's fid set but NOT severity_b's.
Empty or unknown severity -> frozenset().  Asymmetric.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: set DIFFERENCE (not intersection) over severity-filtered fids.
     fids exclusive to severity_a (not shared with severity_b).
     Kills impl reusing severity_pair_co_occurrence (which gives intersection).
  2. Returns frozenset[str] (fid strings), not int.
     Kills impl returning count like severity_pair_co_occurrence.
  3. Asymmetric: swap args -> different result.
     Kills symmetric (commutative) impl.
  4. Unknown severity -> frozenset() (not raise).
     Kills impl that errors on missing severity.
  5. Empty -> frozenset() (not raise).
     Kills impl with unguarded access.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_pair_exclusive_fids,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fids_in_a_not_in_b() -> None:
    """PRIMARY DISC.: set-difference, not intersection.

    HIGH has {f1, f2}, LOW has {f2, f3}.
    Exclusive to HIGH = {f1} (not {f2} which is co-occurring).
    Kills impl returning the intersection {f2}.
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f2", "LOW"),
        _p("c", "f3", "LOW"),
    ]
    result = severity_pair_exclusive_fids(problems, "HIGH", "LOW")
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert result == frozenset({"f1"}), "Only f1 is exclusive to HIGH; got " + repr(result)


def test_returns_frozenset_not_int() -> None:
    """Returns frozenset[str], not int like severity_pair_co_occurrence."""
    problems = [_p("c", "x", "HIGH"), _p("c", "y", "LOW")]
    result = severity_pair_exclusive_fids(problems, "HIGH", "LOW")
    assert isinstance(result, frozenset), "Must be frozenset; got " + repr(type(result))
    assert result == frozenset({"x"}), "x exclusive to HIGH; got " + repr(result)


def test_asymmetric_swap_gives_different_result() -> None:
    """Swapping args returns a different (complementary) result."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f2", "LOW"),
        _p("c", "f3", "LOW"),
    ]
    high_minus_low = severity_pair_exclusive_fids(problems, "HIGH", "LOW")
    low_minus_high = severity_pair_exclusive_fids(problems, "LOW", "HIGH")
    assert high_minus_low != low_minus_high, "Should be asymmetric; both returned " + repr(
        high_minus_low
    )
    assert high_minus_low == frozenset({"f1"}), "HIGH-LOW={f1}; got " + repr(high_minus_low)
    assert low_minus_high == frozenset({"f3"}), "LOW-HIGH={f3}; got " + repr(low_minus_high)


def test_unknown_severity_returns_empty_frozenset() -> None:
    """Unknown severity (either arg) -> frozenset(), not raise."""
    problems = [_p("c", "F001", "HIGH")]
    result = severity_pair_exclusive_fids(problems, "HIGH", "NONEXISTENT")
    assert result == frozenset(), "Unknown severity_b -> frozenset(); got " + repr(result)


def test_empty_returns_empty_frozenset() -> None:
    """Empty input returns frozenset(), not raise."""
    result = severity_pair_exclusive_fids([], "HIGH", "LOW")
    assert result == frozenset(), "Empty -> frozenset(); got " + repr(result)
    assert isinstance(result, frozenset)
