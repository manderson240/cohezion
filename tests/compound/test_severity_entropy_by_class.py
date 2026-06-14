"""Item 318: severity_entropy_by_class() — Shannon entropy of severity distribution per class (2026-06-08).

``severity_entropy_by_class(problems) -> dict[str, float]``:
Returns {class: H} where H = -sum(p_i * log2(p_i)) over the labelled severity
fractions within that class.  Denominator = total problems in that class (NOT
global total).  Unlabelled problems (severity='') are excluded from the
distribution but count towards the denominator.  Classes with no labelled
problems return entropy 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: denominator uses class-local total, not global total.
     Kills impl that divides by len(problems) instead of per-class count.
  2. Single-severity class has entropy 0.0.
     Kills impl returning non-zero for a pure-severity distribution.
  3. Two-equal-severity class has entropy exactly 1.0 (log2(2)=1.0).
     Kills impl using natural log (ln) instead of log2.
  4. Class with ONLY unlabelled problems returns entropy 0.0 (not omitted).
     Kills impl that raises ZeroDivisionError or omits the class entirely.
  5. Empty input returns {}.
     Kills impl that crashes on empty list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_entropy_by_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_denominator_is_class_local_not_global() -> None:
    """Denominator = class total, NOT global total.

    PRIMARY DISCRIMINATOR: kills impl using len(problems) as denominator.
    alpha: 2 HIGH, 0 LOW (out of 4 total problems).
    beta: 1 HIGH, 1 LOW (2 beta problems total).
    If wrong impl uses global total (4): p_beta_HIGH=1/4, p_beta_LOW=1/4 → H=-2*(0.25*log2(0.25))=1.0? No,
    but the fractions must sum to 1 per class, so global denominator would give p=0.5 each anyway for beta.
    Use a 3-class scenario with unequal sizes: alpha has 3 HIGH out of 3 → H=0;
    beta has 1 HIGH + 1 LOW out of 6 TOTAL (2 beta-specific).
    Wrong impl uses total=6: p=1/6, p=1/6 (don't sum to 1) → H≠1.0.
    """
    problems = [
        _p("alpha", 0, "HIGH"),
        _p("alpha", 1, "HIGH"),
        _p("alpha", 2, "HIGH"),
        _p("beta", 0, "HIGH"),  # beta-local: 2 problems
        _p("beta", 1, "LOW"),
    ]
    result = severity_entropy_by_class(problems)
    # alpha: only HIGH -> entropy = 0.0
    assert abs(result["alpha"] - 0.0) < 1e-9, (
        f"alpha all-HIGH -> H=0.0; got {result.get('alpha')!r}"
    )
    # beta: 1 HIGH + 1 LOW out of 2 -> p=0.5 each -> H=1.0 (log2 base)
    assert abs(result["beta"] - 1.0) < 1e-9, (
        f"beta equal split -> H=1.0; got {result.get('beta')!r}"
    )


def test_single_severity_class_entropy_is_zero() -> None:
    """Class with only one distinct labelled severity has entropy 0.0.

    Kills impl returning non-zero for a single-category distribution.
    """
    problems = [_p("alpha", 0, "HIGH"), _p("alpha", 1, "HIGH"), _p("alpha", 2, "HIGH")]
    result = severity_entropy_by_class(problems)
    assert abs(result.get("alpha", -1) - 0.0) < 1e-9, "alpha all-HIGH -> H=0.0; got " + repr(
        result.get("alpha")
    )


def test_two_equal_severities_entropy_is_one_bit() -> None:
    """Two equally-distributed severities -> H = 1.0 bit (log2 base).

    Kills impl using natural log (H would be ≈0.693 with ln).
    """
    problems = [_p("alpha", 0, "HIGH"), _p("alpha", 1, "LOW")]
    result = severity_entropy_by_class(problems)
    assert abs(result.get("alpha", -1) - 1.0) < 1e-9, (
        "alpha 1-HIGH 1-LOW -> H=1.0 bit; got " + repr(result.get("alpha"))
    )


def test_class_with_only_unlabelled_returns_zero_not_omitted() -> None:
    """Class with ONLY unlabelled problems returns 0.0 (not omitted).

    Kills impl that raises ZeroDivisionError or skips the class.
    beta has only unlabelled problems; it should still appear with H=0.0.
    alpha has one labelled problem for contrast.
    """
    problems = [
        _p("alpha", 0, "HIGH"),
        _p("beta", 0, ""),
        _p("beta", 1, ""),
    ]
    result = severity_entropy_by_class(problems)
    assert "beta" in result, "beta has only unlabelled -> still in result with H=0.0; got " + repr(
        result
    )
    assert abs(result["beta"] - 0.0) < 1e-9, "beta all-unlabelled -> H=0.0; got " + repr(
        result.get("beta")
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {}.

    Kills impl that crashes on empty list.
    """
    result = severity_entropy_by_class([])
    assert result == {}, "empty -> {}; got " + repr(result)
