"""Item 674: fid_distinct_class_count() -- count of unique classes per fid.

Fid-axis complement of class_distinct_fid_count (item 673).
Returns {fid: distinct_class_count}.  int >= 1.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID (NOT class); counts distinct classes per fid.
     fid 'f1' in class A (×2) and class B (×3) -> distinct_class_count=2 (not total=5).
     Kills class-outer impl (item 673 copy) and total-count impl.
  2. Single class repeated for a fid -> distinct_count=1.
  3. Empty -> {}.
  4. Multiple fids get independent class counts.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_distinct_class_count


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_fid_outer_key_distinct_classes_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID NOT class; counts distinct classes per fid.

    fid 'f1': class A (2 problems), class B (3 problems) -> distinct_class_count=2.
    Kills class-outer impl (item 673 copy) and total-count impl (5 wrong).
    """
    problems = [_p("A", "f1")] * 2 + [_p("B", "f1")] * 3
    result = fid_distinct_class_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"Fid 'f1' must be outer key; got {list(result)}"
    # Class-axis wrong: result would be keyed by class not fid
    assert result["f1"] == 2, (
        f"f1 in 2 distinct classes (A,B) -> count=2; got {result['f1']} "
        f"(total=5 wrong, class-outer wrong)"
    )
    assert isinstance(result["f1"], int), "Must be int"


def test_single_class_repeated_is_one() -> None:
    """Same class repeated many times for a fid -> distinct_count=1."""
    problems = [_p("A", "fx")] * 10
    result = fid_distinct_class_count(problems)
    assert result["fx"] == 1, f"Only class A 10 times -> distinct=1; got {result.get('fx')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_distinct_class_count([]) == {}


def test_multiple_fids_independent_counts() -> None:
    """Different fids get independent distinct class counts."""
    problems = (
        [_p("A", "f1"), _p("B", "f1"), _p("C", "f1")]  # f1 in 3 classes
        + [_p("A", "f2"), _p("A", "f2")]  # f2 in 1 class only
    )
    result = fid_distinct_class_count(problems)
    assert result["f1"] == 3, f"f1 in 3 classes; got {result.get('f1')}"
    assert result["f2"] == 1, f"f2 in 1 class; got {result.get('f2')}"


def test_return_type_is_int() -> None:
    """Return values must be int."""
    result = fid_distinct_class_count([_p("X", "f9"), _p("Y", "f9")])
    assert isinstance(result["f9"], int), f"Must be int; got {type(result['f9'])}"
