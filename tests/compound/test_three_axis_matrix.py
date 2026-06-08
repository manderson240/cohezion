"""Item 474: three_axis_matrix() -- 3-D sparse count tensor (2026-06-08).

``three_axis_matrix(problems) -> dict[str, dict[str, dict[str, int]]]``:
Returns tensor[cls][fid][sev] = count for each observed (class, fid, severity) triple.
Sparse: absent triples absent.  Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: 3-level nesting (not 2).
     ClassA/fid_a/HIGH x2, ClassA/fid_a/LOW x1.
     tensor['ClassA']['fid_a']['HIGH']=2, ['LOW']=1.
     Kills impl reusing class_fid_matrix (only 2 levels).
  2. Count accumulates: same triple x3 -> count=3 (not True or 1).
     Kills impl storing presence flag.
  3. Empty input -> {}.
     Kills impl with unguarded access.
  4. Sparse: missing severity absent from inner dict (no zero entries).
     Kills impl that zero-fills all (class, fid, severity) combinations.
  5. Key order: outer=class, middle=fid, inner=severity.
     Kills impl with wrong nesting axis order.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    three_axis_matrix,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_three_level_nesting_class_fid_severity() -> None:
    """PRIMARY DISC.: 3-level nesting; outer=class, middle=fid, inner=severity.

    ClassA/fid_a: HIGH x2, LOW x1.
    tensor['ClassA']['fid_a']['HIGH']=2; tensor['ClassA']['fid_a']['LOW']=1.
    Kills impl returning only 2 levels (class_fid_matrix).
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "LOW"),
        _p("ClassA", "fid_b", "HIGH"),
        _p("ClassB", "fid_a", "HIGH"),
    ]
    result = three_axis_matrix(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert result["ClassA"]["fid_a"]["HIGH"] == 2, "ClassA/fid_a/HIGH=2; got " + repr(result)
    assert result["ClassA"]["fid_a"]["LOW"] == 1, "ClassA/fid_a/LOW=1; got " + repr(result)
    assert result["ClassA"]["fid_b"]["HIGH"] == 1, "ClassA/fid_b/HIGH=1; got " + repr(result)
    assert result["ClassB"]["fid_a"]["HIGH"] == 1, "ClassB/fid_a/HIGH=1; got " + repr(result)


def test_count_accumulates_not_presence_flag() -> None:
    """Same triple x3 -> count=3 (not True/1)."""
    problems = [_p("C", "f", "HIGH") for _ in range(3)]
    result = three_axis_matrix(problems)
    assert result["C"]["f"]["HIGH"] == 3, "3 records -> count=3; got " + repr(result)


def test_empty_returns_empty_dict() -> None:
    """Empty input -> {} (not raise)."""
    result = three_axis_matrix([])
    assert result == {}, "Empty -> {}; got " + repr(result)


def test_sparse_absent_severities_absent() -> None:
    """Absent severity not present in inner dict (sparse, no zero-fill)."""
    problems = [_p("ClassA", "fid_a", "HIGH")]
    result = three_axis_matrix(problems)
    inner = result.get("ClassA", {}).get("fid_a", {})
    assert "LOW" not in inner, "LOW absent (sparse); inner=" + repr(inner)
    assert "ClassB" not in result, "ClassB absent (sparse)"


def test_key_order_outer_class_middle_fid_inner_severity() -> None:
    """Outer key = class, middle key = fid, inner key = severity (canonical order)."""
    problems = [_p("MyClass", "my_fid", "CRITICAL")]
    result = three_axis_matrix(problems)
    # Access path must be [class][fid][severity]
    assert result["MyClass"]["my_fid"]["CRITICAL"] == 1
    # Wrong orders should not exist
    assert "my_fid" not in result, "fid must not be outer key"
    assert "CRITICAL" not in result, "severity must not be outer key"
