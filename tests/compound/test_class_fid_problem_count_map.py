"""Item 666: class_fid_problem_count_map() -- cross-tab of class x fid problem counts.

Returns {class: {fid: count}}.  2D nested dict.  Sparse.  Empty -> {}.
Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: returns NESTED dict (NOT flat, NOT per-axis sum).
     class A, fid 'f1': 3 problems -> result['A']['f1']=3.
     Flat-dict ('A'->3 or 'f1'->3) is wrong; kills flat impl.
  2. Sparse: missing fid for a class NOT in inner dict.
     class A: f1=3, class B: f2=2 -> A has no f2 key, B has no f1 key.
  3. Multiple fids per class: each fid counted independently.
     class A: f1=3, f2=1 -> inner dict {'f1': 3, 'f2': 1}.
  4. Same fid in different classes: counts are per-class independent.
     class A: f1=3, class B: f1=2 -> A['f1']=3, B['f1']=2.
  5. Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_fid_problem_count_map


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_nested_dict_not_flat_primary_discriminator() -> None:
    """PRIMARY DISC.: result is a 2D nested dict, NOT a flat dict.

    class A, fid 'f1': 3 problems -> result['A']['f1']=3.
    Flat dict {'A': 3} or {'f1': 3} is wrong; kills flat impl.
    """
    problems = [_p("A", "f1")] * 3
    result = class_fid_problem_count_map(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be outer key; got {list(result)}"
    assert isinstance(result["A"], dict), (
        f"Inner value must be dict (nested); got {type(result['A']).__name__}"
    )
    assert "f1" in result["A"], f"fid 'f1' must be inner key; got {list(result['A'])}"
    assert result["A"]["f1"] == 3, (
        f"class A, fid f1: 3 problems -> count=3; got {result['A']['f1']} (flat dict wrong)"
    )


def test_sparse_missing_fid_absent_in_class() -> None:
    """Sparse: class A has no f2 key; class B has no f1 key."""
    problems = [_p("A", "f1")] * 3 + [_p("B", "f2")] * 2
    result = class_fid_problem_count_map(problems)
    assert result["A"]["f1"] == 3, f"A.f1=3; got {result.get('A', {}).get('f1')}"
    assert result["B"]["f2"] == 2, f"B.f2=2; got {result.get('B', {}).get('f2')}"
    assert "f2" not in result["A"], f"A must not have f2 (sparse); got {result['A']}"
    assert "f1" not in result["B"], f"B must not have f1 (sparse); got {result['B']}"


def test_multiple_fids_per_class_counted_independently() -> None:
    """class A: f1=3, f2=1 -> inner dict {f1:3, f2:1}."""
    problems = [_p("A", "f1")] * 3 + [_p("A", "f2")]
    result = class_fid_problem_count_map(problems)
    assert result["A"]["f1"] == 3, f"A.f1=3; got {result['A'].get('f1')}"
    assert result["A"]["f2"] == 1, f"A.f2=1; got {result['A'].get('f2')}"


def test_same_fid_different_classes_counted_per_class() -> None:
    """Same fid in different classes: A['f1']=3, B['f1']=2 (not merged)."""
    problems = [_p("A", "f1")] * 3 + [_p("B", "f1")] * 2
    result = class_fid_problem_count_map(problems)
    assert result["A"]["f1"] == 3, f"A.f1=3; got {result.get('A', {}).get('f1')}"
    assert result["B"]["f1"] == 2, f"B.f1=2; got {result.get('B', {}).get('f1')}"


def test_empty_returns_empty_dict() -> None:
    """Empty input -> {}."""
    assert class_fid_problem_count_map([]) == {}
