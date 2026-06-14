"""Item 711: fid_severity_rank_weighted_sum() -- custom-weight severity sum per fid.

Fid-axis complement of class_severity_rank_weighted_sum (item 710).
fid_severity_rank_weighted_sum(problems, weights) -> dict[str, float].
Missing severities use 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID, uses SUPPLIED weights;
     fid 'f1': CRITICAL+HIGH, weights={'CRITICAL':10.0,'HIGH':3.0} -> 13.0;
     class-outer wrong; rank-sum gives 7.0 wrong.
  2. Missing severity key -> 0.0 (no KeyError).
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_weighted_sum


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_custom_weights_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND uses supplied weights.

    fid 'f1': CRITICAL+HIGH, weights={'CRITICAL':10.0,'HIGH':3.0} -> 13.0.
    class-outer wrong (key='A'); rank-sum gives 7.0 wrong.
    """
    problems = [_p("f1", "CRITICAL"), _p("f1", "HIGH")]
    weights = {"CRITICAL": 10.0, "HIGH": 3.0}
    result = fid_severity_rank_weighted_sum(problems, weights)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    assert result["f1"] == 13.0, (
        f"CRITICAL(10)+HIGH(3)=13.0; rank-sum=7.0 wrong; got {result['f1']}"
    )
    assert isinstance(result["f1"], float), f"Must be float; got {type(result['f1'])}"


def test_missing_severity_key_gives_zero() -> None:
    """Severity not in weights contributes 0.0."""
    problems = [_p("f2", "LOW"), _p("f2", "CRITICAL")]
    weights = {"CRITICAL": 5.0}
    result = fid_severity_rank_weighted_sum(problems, weights)
    assert result["f2"] == 5.0, f"LOW->0.0 + CRITICAL->5.0 = 5.0; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_weighted_sum([], {"HIGH": 1.0}) == {}


def test_multiple_fids_independent() -> None:
    """Each fid summed independently."""
    problems = [_p("f3", "HIGH"), _p("f3", "HIGH")]  # f3: 2 * 3.0 = 6.0
    problems += [_p("f4", "MEDIUM"), _p("f4", "LOW")]  # f4: 2.0 + 1.0 = 3.0
    weights = {"HIGH": 3.0, "MEDIUM": 2.0, "LOW": 1.0}
    result = fid_severity_rank_weighted_sum(problems, weights)
    assert result["f3"] == 6.0, f"f3: 2xHIGH(3.0) -> 6.0; got {result.get('f3')}"
    assert result["f4"] == 3.0, f"f4: MED(2.0)+LOW(1.0) -> 3.0; got {result.get('f4')}"


def test_all_unknown_severities_give_zero() -> None:
    """All unknown severities -> sum = 0.0."""
    problems = [_p("f5", "UNKNOWN"), _p("f5", "ALSO_UNKNOWN")]
    result = fid_severity_rank_weighted_sum(problems, {"HIGH": 1.0})
    assert result["f5"] == 0.0, f"No known severities -> 0.0; got {result.get('f5')}"
