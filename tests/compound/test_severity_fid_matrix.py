"""Item 448: severity_fid_matrix() -- 2-D severity × finding_id count matrix (2026-06-08).

``severity_fid_matrix(problems) -> dict[str, dict[str, int]]``:
Returns {severity: {finding_id: count}} sparse nested dict.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: outer key is severity (not fid).
     Kills impl reusing fid_severity_matrix with axes unswapped.
  2. Same (severity, fid) pair in multiple records -> count > 1.
     Kills impl that treats fid as unique key (count always 1).
  3. Empty -> {} (not raise).
     Kills impl with unguarded access.
  4. Returns dict[str, dict[str, int]] (nested dicts), not flat dict.
     Validates the structural type of the return value.
  5. Missing (severity, fid) pair absent from matrix (sparse).
     Kills impl that zero-fills all pairs.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_fid_matrix,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_outer_key_is_severity_not_fid() -> None:
    """PRIMARY DISC.: outer key is severity, not fid.

    All problems share fid='f1' but have two distinct severities.
    Outer keys must be severities ('HIGH', 'LOW'), not fid ('f1').
    Kills impl reusing fid_severity_matrix which would produce {'f1': ...}.
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f1", "HIGH"),
        _p("c", "f1", "LOW"),
    ]
    result = severity_fid_matrix(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "HIGH" in result, "Outer key must be severity 'HIGH'; keys=" + repr(list(result))
    assert "LOW" in result, "Outer key must be severity 'LOW'; keys=" + repr(list(result))
    assert "f1" not in result, "Outer key must NOT be fid; got " + repr(list(result))
    assert result["HIGH"]["f1"] == 2, "HIGH→f1=2; got " + repr(result["HIGH"].get("f1"))
    assert result["LOW"]["f1"] == 1, "LOW→f1=1; got " + repr(result["LOW"].get("f1"))


def test_duplicate_records_accumulate_count() -> None:
    """Same (severity, fid) pair in 3 records -> count = 3."""
    problems = [_p(f"c{i}", "F001", "CRITICAL") for i in range(3)]
    result = severity_fid_matrix(problems)
    assert result["CRITICAL"]["F001"] == 3, "3 records -> count=3; got " + repr(
        result.get("CRITICAL", {}).get("F001")
    )


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {}, not raise."""
    result = severity_fid_matrix([])
    assert result == {}, "Empty -> {}; got " + repr(result)
    assert isinstance(result, dict)


def test_returns_nested_dicts() -> None:
    """Returns dict[str, dict[str, int]] -- nested dicts, not flat."""
    problems = [_p("c", "f1", "HIGH")]
    result = severity_fid_matrix(problems)
    assert isinstance(result, dict)
    inner = result.get("HIGH")
    assert isinstance(inner, dict), "Inner must be dict; got " + repr(type(inner))
    assert inner == {"f1": 1}, "Inner = {'f1': 1}; got " + repr(inner)


def test_sparse_missing_pairs_absent() -> None:
    """(severity, fid) pairs not in input are absent (sparse, not zero-filled)."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "LOW"),
    ]
    result = severity_fid_matrix(problems)
    assert "HIGH" in result and "LOW" in result
    # HIGH should NOT contain f2; LOW should NOT contain f1
    assert "f2" not in result["HIGH"], "HIGH should not have f2 (sparse); got " + repr(result["HIGH"])
    assert "f1" not in result["LOW"], "LOW should not have f1 (sparse); got " + repr(result["LOW"])
