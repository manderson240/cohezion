"""Item 715: class_severity_entropy_all() -- Shannon entropy per class (vectorized dict).

class_severity_entropy_all(problems) -> dict[str, float].
H = -sum(p_i * log2(p_i)) over severity distribution per class.
Single-severity -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: equal-split CRITICAL+HIGH (p=0.5 each) -> entropy=1.0 bit;
     count-impl gives 2 wrong; total-count wrong; kills all non-entropy impls.
  2. Single severity label -> 0.0 (no uncertainty).
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Return type is float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_entropy_all


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_equal_split_gives_one_bit_primary_discriminator() -> None:
    """PRIMARY DISC.: equal CRITICAL+HIGH -> entropy = 1.0 bit.

    class A: 1 CRITICAL + 1 HIGH -> p=0.5 each -> H = -2*(0.5*log2(0.5)) = 1.0.
    count-impl gives 2 wrong; single-label gives 0 wrong.
    """
    problems = [_p("A", "CRITICAL"), _p("A", "HIGH")]
    result = class_severity_entropy_all(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    assert abs(result["A"] - 1.0) < 1e-9, (
        f"Equal CRITICAL+HIGH -> H=1.0 bit; got {result['A']} (count-impl=2 wrong)"
    )
    assert isinstance(result["A"], float), f"Must be float; got {type(result['A'])}"


def test_single_severity_gives_zero() -> None:
    """Single severity label -> entropy = 0.0 (no uncertainty)."""
    problems = [_p("B", "CRITICAL")] * 5
    result = class_severity_entropy_all(problems)
    assert result["B"] == 0.0, f"All CRITICAL -> H=0.0; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_entropy_all([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class has its own entropy computed independently."""
    # class C: 2 CRITICAL, 2 HIGH (equal split) -> H=1.0
    problems = [_p("C", "CRITICAL"), _p("C", "CRITICAL"), _p("C", "HIGH"), _p("C", "HIGH")]
    # class D: all MEDIUM -> H=0.0
    problems += [_p("D", "MEDIUM")] * 3
    result = class_severity_entropy_all(problems)
    assert abs(result["C"] - 1.0) < 1e-9, f"C equal split -> H=1.0; got {result.get('C')}"
    assert result["D"] == 0.0, f"D all same -> H=0.0; got {result.get('D')}"


def test_four_equal_labels_give_two_bits() -> None:
    """4 equal-probability severity labels -> H = log2(4) = 2.0 bits."""
    problems = [_p("E", "CRITICAL"), _p("E", "HIGH"), _p("E", "MEDIUM"), _p("E", "LOW")]
    result = class_severity_entropy_all(problems)
    assert abs(result["E"] - 2.0) < 1e-9, f"4 equal labels -> H=2.0 bits; got {result.get('E')}"
