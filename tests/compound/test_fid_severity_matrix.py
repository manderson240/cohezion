"""Item 435: fid_severity_matrix() -- 2-D finding_id × severity count matrix (2026-06-08).

``fid_severity_matrix(problems) -> dict[str, dict[str, int]]``:
Returns {fid: {severity: count}} sparse nested dict.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: outer key is finding_id (not problem_class).
     Kills impl reusing class_severity_matrix on the wrong field.
  2. 2-D structure -- inner values are dicts, not ints.
     Kills impl returning a flat severity histogram.
  3. Sparse -- missing fid+severity combos absent.
     Kills zero-filling impl.
  4. Inner counts correct for multiple records.
     Validates counting logic beyond presence check.
  5. Empty -> {} (not raise).
     Kills impl with unguarded access.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fid_severity_matrix,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_outer_key_is_finding_id_not_class() -> None:
    """PRIMARY DISC.: outer key = finding_id, not problem_class.

    All problems have class 'BUG'. Outer keys must be fids, not 'BUG'.
    Kills impl using p.problem_class as outer key.
    """
    problems = [
        _p("BUG", "f1", "HIGH"),
        _p("BUG", "f2", "LOW"),
        _p("BUG", "f1", "HIGH"),
    ]
    result = fid_severity_matrix(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    # Outer keys must be fids, not class names
    assert set(result.keys()) == {"f1", "f2"}, (
        "Outer keys are fids; got " + repr(set(result.keys()))
    )
    # Inner key is severity
    assert result["f1"]["HIGH"] == 2, "f1/HIGH=2; got " + repr(result["f1"].get("HIGH"))
    assert result["f2"]["LOW"] == 1, "f2/LOW=1; got " + repr(result["f2"].get("LOW"))


def test_two_dimensional_inner_dict_structure() -> None:
    """Inner values are dicts (2-D), not plain ints (1-D)."""
    problems = [_p("cls", "fid1", "HIGH"), _p("cls", "fid1", "LOW")]
    result = fid_severity_matrix(problems)
    assert isinstance(result["fid1"], dict), "Inner must be dict; got " + repr(type(result["fid1"]))


def test_sparse_missing_combos_absent() -> None:
    """fid1 has no LOW, fid2 has no HIGH -- both absent in sparse matrix."""
    problems = [
        _p("cls", "fid1", "HIGH"),
        _p("cls", "fid2", "LOW"),
    ]
    result = fid_severity_matrix(problems)
    assert "LOW" not in result.get("fid1", {}), "fid1/LOW absent; got " + repr(result)
    assert "HIGH" not in result.get("fid2", {}), "fid2/HIGH absent; got " + repr(result)


def test_counts_multiple_records_correctly() -> None:
    """Multiple records with same fid+severity counted correctly."""
    problems = [
        _p("cls", "fx", "CRITICAL"),
        _p("cls", "fx", "CRITICAL"),
        _p("cls", "fx", "CRITICAL"),
    ]
    result = fid_severity_matrix(problems)
    assert result["fx"]["CRITICAL"] == 3, "Three fx/CRITICAL -> 3; got " + repr(result)


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {}."""
    result = fid_severity_matrix([])
    assert result == {}, "Empty -> {}; got " + repr(result)
    assert isinstance(result, dict)
