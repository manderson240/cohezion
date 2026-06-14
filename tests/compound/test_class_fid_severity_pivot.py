"""Item 667: class_fid_severity_pivot() -- 3D cross-tab of class x fid x severity counts.

Returns {class: {fid: {severity: count}}} — 3D sparse pivot table.
Missing combinations absent.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_fid_severity_pivot


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_3d_nested_not_2d_primary_discriminator() -> None:
    """PRIMARY DISC.: returns 3D nested dict, NOT 2D or flat.

    Class A, fid 'f1', severity 'HIGH': 3 problems -> result['A']['f1']['HIGH']=3.
    Flat or 2D result wrong. Kills 2D class_fid_problem_count_map-style impl.
    """
    problems = [_p("A", "f1", "HIGH")] * 3
    result = class_fid_severity_pivot(problems)
    assert isinstance(result, dict), "Outer must be dict"
    assert "A" in result, f"Class 'A' outer key; got {list(result)}"
    assert isinstance(result["A"], dict), "Middle must be dict"
    assert "f1" in result["A"], f"fid 'f1' middle key; got {list(result['A'])}"
    assert isinstance(result["A"]["f1"], dict), "Inner must be dict"
    assert "HIGH" in result["A"]["f1"], f"sev 'HIGH' inner key; got {list(result['A']['f1'])}"
    assert result["A"]["f1"]["HIGH"] == 3, (
        f"3 HIGH -> count=3; got {result['A']['f1']['HIGH']} (2D wrong)"
    )
    assert isinstance(result["A"]["f1"]["HIGH"], int), "Count must be int"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_fid_severity_pivot([]) == {}


def test_sparse_missing_combinations_absent() -> None:
    """Missing class/fid/severity combinations are absent (not zero-filled)."""
    problems = [_p("A", "f1", "HIGH")] * 2
    result = class_fid_severity_pivot(problems)
    assert "LOW" not in result["A"]["f1"], f"'LOW' must be absent; got {result['A']['f1']}"
    assert "B" not in result, f"'B' must be absent; got {list(result)}"


def test_multiple_severities_same_cell() -> None:
    """Multiple severities at same class/fid -> all present in inner dict."""
    problems = (
        [_p("A", "f1", "HIGH")] * 2 + [_p("A", "f1", "LOW")] * 3 + [_p("A", "f1", "CRITICAL")]
    )
    result = class_fid_severity_pivot(problems)
    assert result["A"]["f1"]["HIGH"] == 2
    assert result["A"]["f1"]["LOW"] == 3
    assert result["A"]["f1"]["CRITICAL"] == 1


def test_multiple_classes_fids_severities_independent() -> None:
    """Full 3D independence: different cells don't bleed into each other."""
    problems = [_p("A", "f1", "HIGH")] * 4 + [_p("B", "f2", "LOW")] * 5
    result = class_fid_severity_pivot(problems)
    assert result["A"]["f1"]["HIGH"] == 4
    assert result["B"]["f2"]["LOW"] == 5
    assert "f2" not in result.get("A", {})
    assert "f1" not in result.get("B", {})
