"""Item 602: class_severity_gini() -- Gini impurity of severity distribution per class.

``class_severity_gini(problems) -> dict[str, float]``:
Returns {class: gini_impurity} where gini = 1 - sum(p_i^2).
Single-severity class -> 0.0.  Uniform 2-label -> 0.5.  Empty -> {}.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: Gini (1 - sum(p^2)) not Shannon entropy (-sum(p*log2(p))).
     Uniform 2-severity class -> Gini=0.5; entropy=1.0.
     Kills impl reusing class_severity_entropies (would return 1.0 not 0.5).
  2. Single-severity -> 0.0 (pure class).
     Kills impl always returning non-zero.
  3. Uniform 3-severity -> 2/3 (approximately 0.6667).
     Kills impl using wrong formula.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Non-uniform distribution computed correctly.
     p=[0.75, 0.25] -> 1 - (0.75^2 + 0.25^2) = 1 - 0.625 = 0.375.
     Kills impl assuming equal weights.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_gini


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_gini_not_shannon_entropy_primary_discriminator() -> None:
    """PRIMARY DISC.: Gini impurity (1 - sum(p^2)), NOT Shannon entropy.

    Uniform 2-severity class (HIGH x1, LOW x1):
    Gini = 1 - (0.5^2 + 0.5^2) = 1 - 0.5 = 0.5.
    Shannon entropy = 1.0 (log2(2)).
    Kills impl reusing class_severity_entropies.
    """
    problems = [_p("A", "HIGH"), _p("A", "LOW")]
    result = class_severity_gini(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {list(result)}"
    assert abs(result["A"] - 0.5) < 1e-9, (
        f"Uniform 2-severity Gini=0.5; got {result['A']} (1.0 = Shannon entropy, wrong formula)"
    )


def test_single_severity_gini_zero() -> None:
    """Single severity -> Gini=0.0 (perfectly pure class).

    Kills impl always returning non-zero.
    """
    problems = [_p("A", "HIGH")] * 5
    result = class_severity_gini(problems)
    assert abs(result["A"]) < 1e-9, f"Single-severity -> Gini=0.0; got {result['A']}"


def test_uniform_three_severity_gini() -> None:
    """Uniform 3-severity class -> Gini = 2/3 (approx 0.6667).

    Gini = 1 - 3*(1/3)^2 = 1 - 1/3 = 2/3.
    Kills impl using wrong formula.
    """
    problems = [_p("A", "HIGH"), _p("A", "MEDIUM"), _p("A", "LOW")]
    result = class_severity_gini(problems)
    expected = 2.0 / 3.0
    assert abs(result["A"] - expected) < 1e-9, (
        f"Uniform 3-severity Gini=2/3={expected:.6f}; got {result['A']}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise)."""
    result = class_severity_gini([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_non_uniform_distribution() -> None:
    """Non-uniform p=[0.75, 0.25] -> Gini=0.375.

    1 - (0.75^2 + 0.25^2) = 1 - (0.5625 + 0.0625) = 1 - 0.625 = 0.375.
    Kills impl assuming equal weights.
    """
    # A: HIGH x3, LOW x1 -> p=[0.75, 0.25]
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")]
    result = class_severity_gini(problems)
    expected = 0.375
    assert abs(result["A"] - expected) < 1e-9, f"p=[0.75,0.25]: Gini=0.375; got {result['A']}"
