"""Item 603: fid_severity_gini() -- Gini impurity of severity distribution per fid.

``fid_severity_gini(problems) -> dict[str, float]``:
Returns {fid: 1 - sum(p_i^2)}.  FID-axis complement of class_severity_gini.
Single-severity -> 0.0.  Uniform 2-label -> 0.5.  Empty -> {}.

Discriminating tests:
  1. PRIMARY DISC.: keyed by FID (not class).
  2. Same 1-sum(p^2) formula, not Shannon entropy.
  3. Single-severity -> 0.0.
  4. Empty -> {}.
  5. Non-uniform: p=[0.75,0.25] -> Gini=0.375.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_gini


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: result keyed by fid, NOT class name."""
    problems = [_p("A", "f1", "HIGH"), _p("A", "f1", "LOW")]
    result = fid_severity_gini(problems)
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {result}"
    assert abs(result["f1"] - 0.5) < 1e-9, f"Uniform 2-severity -> Gini=0.5; got {result['f1']}"


def test_gini_formula_not_shannon_entropy() -> None:
    """Gini (1 - sum(p^2)) not Shannon entropy.

    Uniform 2-severity fid -> Gini=0.5; Shannon=1.0.
    Kills impl reusing class_severity_entropies formula.
    """
    problems = [_p("A", "fx", "HIGH"), _p("B", "fx", "LOW")]
    result = fid_severity_gini(problems)
    assert abs(result["fx"] - 0.5) < 1e-9, (
        f"Uniform [HIGH,LOW] -> Gini=0.5; got {result['fx']} (1.0=Shannon)"
    )


def test_single_severity_gini_zero() -> None:
    """Single severity per fid -> 0.0."""
    problems = [_p("A", "fy", "CRITICAL")] * 4
    result = fid_severity_gini(problems)
    assert abs(result["fy"]) < 1e-9, f"Single-severity -> 0.0; got {result['fy']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_gini([]) == {}


def test_non_uniform_distribution() -> None:
    """p=[0.75, 0.25] -> Gini=0.375."""
    problems = [_p("A", "fz", "HIGH")] * 3 + [_p("B", "fz", "LOW")]
    result = fid_severity_gini(problems)
    assert abs(result["fz"] - 0.375) < 1e-9, f"p=[0.75,0.25] -> Gini=0.375; got {result['fz']}"
