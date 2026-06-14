"""Item 685: fid_severity_all() -- True if ALL problems for a fid match given severity set.

Fid-axis complement of class_severity_all (684).
fid_severity_all(problems, severities) -> dict[str, bool].
Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID and ALL must match (not any).
     fid 'f1': HIGH,LOW -> fid_severity_all(problems, {'HIGH'}) = False (LOW not in {HIGH}).
     Kills class-outer impl AND any-impl in one shot.
  2. True when every problem for fid is in severity set.
  3. Empty -> {}.
  4. Multiple fids, independent.
  5. Empty severity set -> all False.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_all


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_all_not_any_primary_discriminator() -> None:
    """PRIMARY DISC.: key is FID AND ALL must match.

    fid 'f1': HIGH,LOW -> fid_severity_all(problems, {'HIGH'}) = False.
    class-outer impl wrong (would key by 'A'); any-impl wrong (True for HIGH match).
    """
    problems = [_p("f1", "HIGH"), _p("f1", "LOW")]
    result = fid_severity_all(problems, {"HIGH"})
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key (fid-axis); got {list(result)}"
    assert result["f1"] is False, (
        f"HIGH+LOW, query {{HIGH}} -> False (LOW not in set); "
        f"got {result['f1']} (True = any-impl mistake)"
    )
    assert isinstance(result["f1"], bool), "Must be bool"


def test_true_when_all_match() -> None:
    """All problems for fid have severity in set -> True."""
    problems = [_p("f2", "CRITICAL"), _p("f2", "CRITICAL"), _p("f2", "HIGH")]
    result = fid_severity_all(problems, {"CRITICAL", "HIGH"})
    assert result["f2"] is True, (
        f"All CRIT/HIGH, query {{CRIT,HIGH}} -> True; got {result.get('f2')}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_all([], {"HIGH"}) == {}


def test_multiple_fids_independent() -> None:
    """f3: all MEDIUM (in set) -> True; f4: LOW+MEDIUM, LOW not in set -> False."""
    problems = [
        _p("f3", "MEDIUM"),
        _p("f3", "MEDIUM"),
        _p("f4", "LOW"),
        _p("f4", "MEDIUM"),
    ]
    result = fid_severity_all(problems, {"MEDIUM"})
    assert result["f3"] is True, f"f3 all MEDIUM -> True; got {result.get('f3')}"
    assert "f4" in result, "f4 must be present"
    assert result["f4"] is False, f"f4 has LOW -> False; got {result.get('f4')}"


def test_empty_severity_set_all_false() -> None:
    """Empty severity set -> all False."""
    problems = [_p("f5", "HIGH"), _p("f6", "LOW")]
    result = fid_severity_all(problems, set())
    assert result["f5"] is False
    assert result["f6"] is False
