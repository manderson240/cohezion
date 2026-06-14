"""Item 678: class_severity_count_map() -- 2D cross-tab of class x severity problem counts.

Returns {class: {severity: count}}.  2D nested dict.  Sparse.  Empty -> {}.  Pure; no I/O.
NOT the same as class_fid_severity_pivot (item 667) which is 3D class×fid×severity.

Discriminating tests:
  1. PRIMARY DISC.: 2D nested dict keyed class THEN severity (NOT flat, NOT 3D).
     class A: 3 HIGH + 2 LOW -> result['A']['HIGH']=3, result['A']['LOW']=2.
     Kills 1D (class→count) and 3D (class→fid→sev) impl.
  2. Sparse: missing severities absent from inner dict.
  3. Empty -> {}.
  4. Multiple classes get independent severity counts.
  5. All severities present when they appear (case-preserved as-is from input).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_count_map


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_2d_nested_class_then_severity_primary_discriminator() -> None:
    """PRIMARY DISC.: 2D nested dict keyed class THEN severity, NOT flat, NOT 3D.

    class A: 3 HIGH + 2 LOW -> result['A']['HIGH']=3, result['A']['LOW']=2.
    Kills flat {A:5} wrong, kills 3D class->fid->sev wrong.
    """
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")] * 2
    result = class_severity_count_map(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be outer key; got {list(result)}"
    assert isinstance(result["A"], dict), f"Inner must be dict; got {type(result['A'])}"
    assert result["A"]["HIGH"] == 3, f"3 HIGH -> count=3; got {result['A'].get('HIGH')}"
    assert result["A"]["LOW"] == 2, f"2 LOW -> count=2; got {result['A'].get('LOW')}"


def test_sparse_missing_severities_absent() -> None:
    """Missing severities are absent from inner dict (sparse)."""
    problems = [_p("B", "HIGH")] * 4
    result = class_severity_count_map(problems)
    assert result["B"]["HIGH"] == 4, "B/HIGH=4"
    assert "LOW" not in result["B"], f"LOW must be absent; got {result['B']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_count_map([]) == {}


def test_multiple_classes_independent() -> None:
    """Different classes get independent severity counts."""
    problems = [_p("A", "CRITICAL")] * 2 + [_p("A", "HIGH")] * 3 + [_p("B", "LOW")] * 5
    result = class_severity_count_map(problems)
    assert result["A"]["CRITICAL"] == 2
    assert result["A"]["HIGH"] == 3
    assert "LOW" not in result.get("A", {})
    assert result["B"]["LOW"] == 5
    assert "HIGH" not in result.get("B", {})


def test_all_severities_counted_per_class() -> None:
    """All 5 standard severities counted when present."""
    problems = [
        _p("X", "CRITICAL"),
        _p("X", "HIGH"),
        _p("X", "MEDIUM"),
        _p("X", "LOW"),
        _p("X", "INFO"),
    ]
    result = class_severity_count_map(problems)
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        assert result["X"][sev] == 1, f"X/{sev}=1; got {result['X'].get(sev)}"
