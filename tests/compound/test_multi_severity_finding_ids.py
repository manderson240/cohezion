"""Item 312: multi_severity_finding_ids() — finding_ids with 2+ distinct severities (2026-06-08).

``multi_severity_finding_ids(problems) -> frozenset[str]``:
Returns the frozenset of finding_ids that carry 2 or more DISTINCT labelled severity
strings across all their records.  A finding_id with the same severity repeated
many times is excluded (only 1 distinct severity).  Unlabelled records excluded.
Finding_ids with only unlabelled records excluded.  Empty -> frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: requires >=2 DISTINCT labelled severities (not >=2 records).
     Kills impl counting total records (same severity repeated many times -> 1 distinct).
  2. Finding_id with exactly 1 distinct labelled severity is excluded.
     Kills impl returning all finding_ids with labelled records.
  3. Finding_id with >=2 distinct severities is included.
     Kills impl with off-by-one (requires >2 instead of >=2).
  4. Empty input -> frozenset().
     Kills impl that crashes or returns non-empty.
  5. Return type is frozenset[str].
     Kills impl returning list or set.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    multi_severity_finding_ids,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def _pu(cls: str, fid: str) -> Problem:
    """Unlabelled problem."""
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_repeated_same_severity_is_excluded() -> None:
    """Finding_id with same severity repeated many times = 1 distinct -> excluded.

    PRIMARY DISCRIMINATOR: kills impl counting total records not distinct severities.
    f001: 3 HIGH records -> only 1 distinct severity -> NOT in result.
    f002: 1 HIGH + 1 LOW -> 2 distinct severities -> in result.
    """
    problems = [
        _p("alpha", "f001", "HIGH"),
        _p("alpha", "f001", "HIGH"),
        _p("alpha", "f001", "HIGH"),
        _p("beta", "f002", "HIGH"),
        _p("beta", "f002", "LOW"),
    ]
    result = multi_severity_finding_ids(problems)
    assert "f001" not in result, "f001: 3 HIGH (1 distinct) -> excluded; got " + repr(result)
    assert "f002" in result, "f002: HIGH+LOW (2 distinct) -> included; got " + repr(result)


def test_exactly_one_distinct_severity_excluded() -> None:
    """Finding_id with exactly 1 distinct labelled severity is NOT in result.

    Kills impl returning all finding_ids with labelled records.
    f003: only CRITICAL records -> 1 distinct -> excluded.
    """
    problems = [_p("gamma", "f003", "CRITICAL"), _p("gamma", "f003", "CRITICAL")]
    result = multi_severity_finding_ids(problems)
    assert "f003" not in result, "f003: 1 distinct severity -> excluded; got " + repr(result)


def test_exactly_two_distinct_severities_included() -> None:
    """Finding_id with exactly 2 distinct severities IS in result (>=2, not >2).

    Kills impl with off-by-one requiring >2.
    f004: HIGH + LOW -> 2 distinct -> included.
    """
    problems = [_p("delta_cls", "f004", "HIGH"), _p("delta_cls", "f004", "LOW")]
    result = multi_severity_finding_ids(problems)
    assert "f004" in result, "f004: HIGH+LOW (exactly 2 distinct) -> included; got " + repr(result)


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input -> frozenset().

    Kills impl that crashes or returns non-empty.
    """
    result = multi_severity_finding_ids([])
    assert result == frozenset(), "empty -> frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset[str].

    Kills impl returning list or set.
    """
    problems = [_p("epsilon_cls", "f005", "HIGH"), _p("epsilon_cls", "f005", "LOW")]
    result = multi_severity_finding_ids(problems)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
