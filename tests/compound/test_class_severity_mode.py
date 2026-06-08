"""Item 598: class_severity_mode() -- full co-dominant severity set per class (2026-06-08).

``class_severity_mode(problems) -> dict[str, frozenset[str]]``:
Returns {class: frozenset_of_dominant_severity_labels}.
Dominant = ALL severities sharing the maximum count for that class.
Single-dominant class -> singleton frozenset.
Tied class -> frozenset of size > 1.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns frozenset (not a single str like class_top_severity).
     [A: HIGH x2, LOW x2] -> result['A'] == frozenset({'HIGH','LOW'}) (2-element frozenset).
     [B: HIGH x3, LOW x1] -> result['B'] == frozenset({'HIGH'}) (singleton frozenset).
     Kills impl returning a single string winner like class_top_severity.
  2. Singleton case still returns frozenset, not bare str.
     [A: HIGH x5] -> result['A'] == frozenset({'HIGH'}), isinstance frozenset.
     Kills impl returning str for unambiguous case.
  3. Partial tie: only labels at max count are included, not all labels.
     [A: HIGH x3, LOW x3, MEDIUM x1] -> result['A'] == frozenset({'HIGH','LOW'}) (not MEDIUM).
     Kills impl returning all distinct severity labels regardless of count.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Values are frozenset (hashable), not mutable set.
     Kills impl returning mutable set (not hashable, weaker contract).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_mode


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_returns_frozenset_not_single_string_primary_discriminator() -> None:
    """PRIMARY DISC.: returns frozenset (not a single str).

    [A: HIGH x2, LOW x2] -> result['A'] == frozenset({'HIGH','LOW'}).
    [B: HIGH x3, LOW x1] -> result['B'] == frozenset({'HIGH'}).
    Kills impl returning a single string winner.
    """
    problems = (
        [_p("A", "HIGH")] * 2 + [_p("A", "LOW")] * 2 + [_p("B", "HIGH")] * 3 + [_p("B", "LOW")]
    )
    result = class_severity_mode(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result and "B" in result, f"Both classes must be present; got {list(result)}"
    assert result["A"] == frozenset({"HIGH", "LOW"}), (
        f"Tie HIGH=2/LOW=2 -> frozenset({{'HIGH','LOW'}}); got {result['A']!r} "
        f"(a single str = class_top_severity logic, wrong)"
    )
    assert result["B"] == frozenset({"HIGH"}), (
        f"Solo HIGH=3 -> frozenset({{'HIGH'}}); got {result['B']!r}"
    )


def test_singleton_returns_frozenset_not_bare_str() -> None:
    """Singleton dominant still returns frozenset, not a bare str.

    [A: CRITICAL x5] -> result['A'] == frozenset({'CRITICAL'}).
    Kills impl returning bare str for unambiguous case.
    """
    problems = [_p("A", "CRITICAL")] * 5
    result = class_severity_mode(problems)
    assert isinstance(result["A"], frozenset), (
        f"Value must be frozenset; got {type(result['A']).__name__} = {result['A']!r}"
    )
    assert result["A"] == frozenset({"CRITICAL"}), (
        f"Expected frozenset({{'CRITICAL'}}); got {result['A']!r}"
    )


def test_only_max_count_labels_included_not_all() -> None:
    """Only labels at the max count are included — not all distinct labels.

    [A: HIGH x3, LOW x3, MEDIUM x1] -> frozenset({'HIGH','LOW'}) — MEDIUM excluded.
    Kills impl returning all distinct severity labels.
    """
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")] * 3 + [_p("A", "MEDIUM")]
    result = class_severity_mode(problems)
    assert result["A"] == frozenset({"HIGH", "LOW"}), (
        f"Only HIGH=3 and LOW=3 tie at max; MEDIUM=1 must be excluded; got {result['A']!r}"
    )
    assert "MEDIUM" not in result["A"], (
        f"'MEDIUM' (count=1) must NOT be in mode set; got {result['A']!r}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise)."""
    result = class_severity_mode([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_values_are_frozenset_not_mutable_set() -> None:
    """Values are frozenset (hashable), not mutable set.

    Kills impl returning mutable set (not hashable, weaker contract).
    """
    problems = [_p("A", "HIGH"), _p("A", "LOW")]
    result = class_severity_mode(problems)
    val = result["A"]
    assert isinstance(val, frozenset), (
        f"Value must be frozenset (hashable); got {type(val).__name__}"
    )
    # frozenset is hashable; this line proves it
    _ = hash(val)
