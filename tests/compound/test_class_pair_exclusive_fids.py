"""Item 429: class_pair_exclusive_fids() — fids in class_a but not class_b (2026-06-08).

``class_pair_exclusive_fids(problems, class_a, class_b) -> frozenset[str]``:
Returns frozenset of finding_ids that appear in class_a's fid set but NOT class_b's.
Empty or unknown class -> frozenset().  Asymmetric (a-b != b-a in general).  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: set DIFFERENCE (not intersection) — kills impl reusing co_occurrence.
     fids in a-b are EXCLUSIVE to a, not shared with b.
  2. Returns frozenset[str] not int.
     Kills impl returning count like co_occurrence.
  3. Asymmetric: swap args -> different result.
     Kills symmetric (commutative) impl.
  4. Unknown class -> frozenset() (not raise).
     Kills impl that errors on missing key.
  5. Empty -> frozenset() (not raise).
     Kills impl with unguarded access.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_pair_exclusive_fids,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_fids_in_a_not_in_b() -> None:
    """PRIMARY DISC.: set-difference, not intersection.

    class_a has {f1, f2}, class_b has {f2, f3}.
    Exclusive to a = {f1} (not {f2} which is co-occurring).
    Kills impl returning the intersection {f2}.
    """
    problems = [
        _p("alpha", "f1"),
        _p("alpha", "f2"),
        _p("beta", "f2"),
        _p("beta", "f3"),
    ]
    result = class_pair_exclusive_fids(problems, "alpha", "beta")
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert result == frozenset({"f1"}), "Only f1 is exclusive to alpha; got " + repr(result)


def test_returns_frozenset_not_int() -> None:
    """Returns frozenset[str], not int like co_occurrence."""
    problems = [_p("a", "x"), _p("b", "y")]
    result = class_pair_exclusive_fids(problems, "a", "b")
    assert isinstance(result, frozenset), "Must be frozenset; got " + repr(type(result))
    assert result == frozenset({"x"}), "f exclusive to a = {x}; got " + repr(result)


def test_asymmetric_swap_gives_different_result() -> None:
    """Swapping args returns a different (complementary) result -- not commutative."""
    problems = [
        _p("a", "f1"),
        _p("a", "f2"),
        _p("b", "f2"),
        _p("b", "f3"),
    ]
    a_minus_b = class_pair_exclusive_fids(problems, "a", "b")
    b_minus_a = class_pair_exclusive_fids(problems, "b", "a")
    assert a_minus_b != b_minus_a, "Should be asymmetric; both returned " + repr(a_minus_b)
    assert a_minus_b == frozenset({"f1"}), "a-b = {f1}; got " + repr(a_minus_b)
    assert b_minus_a == frozenset({"f3"}), "b-a = {f3}; got " + repr(b_minus_a)


def test_unknown_class_returns_empty_frozenset() -> None:
    """Unknown class (either arg) -> frozenset(), not raise.

    Both classes must exist for a meaningful difference; absent class
    is treated as an unanswerable query -> frozenset() sentinel.
    Kills impl that raises KeyError on absent class.
    """
    problems = [_p("alpha", "F001")]
    result = class_pair_exclusive_fids(problems, "alpha", "NONEXISTENT")
    assert result == frozenset(), "Unknown class_b -> frozenset(); got " + repr(result)


def test_empty_returns_empty_frozenset() -> None:
    """Empty input returns frozenset(), not raise."""
    result = class_pair_exclusive_fids([], "alpha", "beta")
    assert result == frozenset(), "Empty -> frozenset(); got " + repr(result)
    assert isinstance(result, frozenset)
