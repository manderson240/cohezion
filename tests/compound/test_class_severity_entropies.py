"""Item 582: class_severity_entropies() -- Shannon entropy dict for all classes (2026-06-08).

``class_severity_entropies(problems) -> dict[str, float]``:
Returns {class: entropy_bits} for ALL classes.  Shannon entropy H = -sum(p*log2(p)).
Distinct from class_severity_entropy(problems, cls) which returns a single float.
Empty -> {}.  Single-severity class -> 0.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns DICT for ALL classes (not single float like class_severity_entropy).
     Two classes: result has two keys; class_severity_entropy(problems, cls) would give one float.
     Kills impl reusing class_severity_entropy for single class.
  2. Uses log2 (bits, not nats): uniform 2-severity -> 1.0 bit (not ~0.693 nats).
     Kills impl using math.log instead of math.log2.
  3. Single-severity class -> 0.0 (minimum entropy).
     Kills impl returning non-zero for homogeneous class.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Equal mix of 4 severities -> log2(4) = 2.0 bits.
     Kills impl with wrong formula or wrong k.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_entropies


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_dict_for_all_classes_primary_discriminator() -> None:
    """PRIMARY DISC.: returns dict with entry for EVERY class.

    Two classes A and B: result = {'A': ..., 'B': ...} (2 keys).
    class_severity_entropy(problems, 'A') returns a single float -- different arity.
    Kills impl that only computes one class or returns a float.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("A", "f2", "LOW"),
        _p("B", "f3", "HIGH"),
    ]
    result = class_severity_entropies(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class A must be in result; got {result}"
    assert "B" in result, f"Class B must be in result; got {result}"
    assert len(result) == 2, f"Exactly 2 classes; got {result}"


def test_log2_not_natural_log() -> None:
    """Uses log2 (bits), not natural log (nats).

    Uniform 2-severity: H = -2*(0.5*log2(0.5)) = 1.0 bit.
    With natural log: H = -2*(0.5*ln(0.5)) ~= 0.693 nats.
    Kills impl using math.log instead of math.log2.
    """
    problems = [_p("A", "f1", "HIGH"), _p("A", "f2", "LOW")]
    result = class_severity_entropies(problems)
    assert abs(result["A"] - 1.0) < 1e-9, (
        f"Uniform 2-severity -> 1.0 bit; got {result['A']} "
        f"(0.693 = natural log, 1.0 = log2)"
    )


def test_single_severity_returns_zero() -> None:
    """Single severity -> 0.0 (minimum entropy, no uncertainty).

    Kills impl returning non-zero for a homogeneous class.
    """
    problems = [_p("A", f"f{i}", "HIGH") for i in range(5)]
    result = class_severity_entropies(problems)
    assert abs(result["A"]) < 1e-9, f"All-HIGH -> 0.0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = class_severity_entropies([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_four_equal_severities_gives_two_bits() -> None:
    """Equal mix of 4 severities -> log2(4) = 2.0 bits.

    H = -4*(0.25*log2(0.25)) = -4*(-0.5) = 2.0.
    Kills impl with wrong formula or off-by-one in count.
    """
    problems = [
        _p("A", "f1", "CRITICAL"),
        _p("A", "f2", "HIGH"),
        _p("A", "f3", "MEDIUM"),
        _p("A", "f4", "LOW"),
    ]
    result = class_severity_entropies(problems)
    expected = math.log2(4)  # = 2.0
    assert abs(result["A"] - expected) < 1e-9, (
        f"4 equal severities -> {expected} bits; got {result['A']}"
    )
