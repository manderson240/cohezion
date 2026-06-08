"""Item 710: class_severity_rank_weighted_sum() -- custom-weight severity sum per class.

class_severity_rank_weighted_sum(problems, weights) -> dict[str, float].
weights maps severity label to float weight; missing severities use 0.0.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: uses SUPPLIED weights not _SEVERITY_RANK;
     class A: CRITICAL+HIGH, weights={'CRITICAL':10.0,'HIGH':3.0} -> 13.0;
     rank-sum-impl gives 4+3=7 wrong.
  2. Missing severity key -> weight 0.0 (no KeyError).
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Return type is float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_weighted_sum


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_custom_weights_not_rank_sum_primary_discriminator() -> None:
    """PRIMARY DISC.: uses caller weights NOT _SEVERITY_RANK.

    class A: CRITICAL+HIGH, weights={'CRITICAL':10.0,'HIGH':3.0} -> 13.0.
    rank-sum gives 4+3=7 wrong; kills default-rank impl.
    """
    problems = [_p("A", "CRITICAL"), _p("A", "HIGH")]
    weights = {"CRITICAL": 10.0, "HIGH": 3.0}
    result = class_severity_rank_weighted_sum(problems, weights)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    assert result["A"] == 13.0, (
        f"CRITICAL(10)+HIGH(3)=13.0; rank-sum=7.0 wrong; got {result['A']}"
    )
    assert isinstance(result["A"], float), f"Must be float; got {type(result['A'])}"


def test_missing_severity_key_gives_zero() -> None:
    """Severity not in weights contributes 0.0 (no KeyError)."""
    problems = [_p("B", "LOW"), _p("B", "CRITICAL")]
    weights = {"CRITICAL": 5.0}  # LOW not in weights
    result = class_severity_rank_weighted_sum(problems, weights)
    assert result["B"] == 5.0, f"LOW->0.0, CRITICAL->5.0 -> sum=5.0; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_weighted_sum([], {"HIGH": 1.0}) == {}


def test_multiple_classes_independent() -> None:
    """Each class summed independently."""
    problems = [_p("C", "HIGH"), _p("C", "HIGH")]  # C: 2 * 3.0 = 6.0
    problems += [_p("D", "MEDIUM"), _p("D", "LOW")]  # D: 2.0 + 1.0 = 3.0
    weights = {"HIGH": 3.0, "MEDIUM": 2.0, "LOW": 1.0}
    result = class_severity_rank_weighted_sum(problems, weights)
    assert result["C"] == 6.0, f"C: 2xHIGH(3.0) -> 6.0; got {result.get('C')}"
    assert result["D"] == 3.0, f"D: MED(2.0)+LOW(1.0) -> 3.0; got {result.get('D')}"


def test_all_unknown_severities_give_zero() -> None:
    """All severities unknown -> all weights 0.0 -> sum = 0.0."""
    problems = [_p("E", "UNKNOWN"), _p("E", "ALSO_UNKNOWN")]
    result = class_severity_rank_weighted_sum(problems, {"HIGH": 1.0})
    assert result["E"] == 0.0, f"No known severities -> 0.0; got {result.get('E')}"
