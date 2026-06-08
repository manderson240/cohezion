"""Item 318: severity_entropy_map() — Shannon entropy of severity distribution per class (2026-06-08).

``severity_entropy_map(problems) -> dict[str, float]``:
Returns {class: H} where H = -sum(p_i * log2(p_i)) over labelled-severity fractions
for that class.  Denominator = total LABELLED problems in the class (consistent with
the existing single-class class_severity_entropy helper).  Classes with zero labelled
problems return entropy 0.0 and ARE included in the result.  Empty -> {}.  Pure; no I/O.

Batch variant of the existing class_severity_entropy(problems, cls) single-class helper.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: entropy = 0.0 for single-severity class.
     Kills impl returning non-zero for a certain (uniform) distribution.
  2. Two equal severities -> exactly 1.0 bit (log2 not ln).
     Kills impl using natural log instead of log2.
  3. Class with only unlabelled problems -> 0.0 (PRESENT in result, not omitted).
     Kills impl omitting classes that have no labelled problems.
  4. Empty input -> {}.
     Kills impl that crashes on empty list.
  5. Uniform 4-way split -> 2.0 bits; strictly greater than 2-way split (1.0 bit).
     Kills impl returning a constant or wrong value.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_entropy_map,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_single_severity_class_has_zero_entropy() -> None:
    """All problems in a class share one severity -> entropy = 0.0.

    PRIMARY DISCRIMINATOR: kills impl returning non-zero for certain distribution.
    alpha: 3 HIGH -> p=1.0 -> H = -1*log2(1) = 0.0.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "HIGH"), _ps("alpha", 2, "HIGH")]
    result = severity_entropy_map(problems)
    assert "alpha" in result, "alpha must be in result; got " + repr(result)
    assert abs(result["alpha"] - 0.0) < 1e-9, "single severity -> H=0.0; got " + repr(
        result["alpha"]
    )


def test_two_equal_severities_give_one_bit() -> None:
    """Equal split across 2 severities -> exactly 1.0 bit.

    Kills impl using natural log (ln) instead of log2 (would give ~0.693).
    alpha: 2 HIGH, 2 LOW -> each p=0.5 -> H = -2*(0.5*log2(0.5)) = 1.0 bit.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "LOW"),
        _ps("alpha", 3, "LOW"),
    ]
    result = severity_entropy_map(problems)
    assert abs(result.get("alpha", -1) - 1.0) < 1e-9, "equal 2-way split -> H=1.0 bit; got " + repr(
        result.get("alpha")
    )


def test_class_with_only_unlabelled_present_with_zero_entropy() -> None:
    """Class with no labelled problems -> present in result with entropy 0.0.

    Kills impl that omits classes lacking labelled problems.
    beta: 3 unlabelled -> result['beta'] = 0.0 (not missing).
    """
    problems = [_ps("alpha", 0, "HIGH"), _p("beta", 0), _p("beta", 1), _p("beta", 2)]
    result = severity_entropy_map(problems)
    assert "beta" in result, "beta (unlabelled only) must be present with H=0.0; got " + repr(
        result
    )
    assert abs(result["beta"] - 0.0) < 1e-9, "unlabelled-only class -> H=0.0; got " + repr(
        result["beta"]
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {} without raising.

    Kills impl that crashes on empty list.
    """
    result = severity_entropy_map([])
    assert result == {}, "empty -> {}; got " + repr(result)


def test_uniform_four_way_split_gives_two_bits_and_exceeds_two_way() -> None:
    """Uniform 4-way split -> 2.0 bits; strictly greater than 2-way (1.0 bit).

    Kills impl returning constant or wrong calculation.
    beta: 1 each CRITICAL/HIGH/MEDIUM/LOW -> H = 2.0 bits.
    alpha: 2 HIGH, 2 LOW -> H = 1.0 bit.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "LOW"),
        _ps("alpha", 3, "LOW"),
        _ps("beta", 0, "CRITICAL"),
        _ps("beta", 1, "HIGH"),
        _ps("beta", 2, "MEDIUM"),
        _ps("beta", 3, "LOW"),
    ]
    result = severity_entropy_map(problems)
    assert abs(result.get("beta", -1) - 2.0) < 1e-9, "4-way uniform -> H=2.0 bits; got " + repr(
        result.get("beta")
    )
    assert result.get("beta", 0) > result.get("alpha", 0), (
        "beta (4-way) must have higher entropy than alpha (2-way); got " + repr(result)
    )
