"""Item 688: fid_severity_none() -- True if NO problem for a fid matches given severity set.

Fid-axis complement of class_severity_none (686).
fid_severity_none(problems, severities) -> dict[str, bool].
Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID and ALL must be ABSENT;
     fid 'f1': HIGH,LOW -> fid_severity_none(problems, {'HIGH'}) = False (HIGH is in set).
     class-outer wrong; any-impl-inverse wrong.
  2. True when NO problem severity is in the set.
  3. Empty -> {}.
  4. Multiple fids, independent.
  5. Empty severity set -> all True.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_none


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_none_primary_discriminator() -> None:
    """PRIMARY DISC.: key is FID AND all must be absent from set.

    fid 'f1': HIGH,LOW -> fid_severity_none(problems, {'HIGH'}) = False.
    fid 'f2': LOW,LOW  -> fid_severity_none(problems, {'HIGH'}) = True.
    class-outer wrong (gives 'A'); any-impl-inverse wrong.
    """
    problems = [
        _p("f1", "HIGH"), _p("f1", "LOW"),
        _p("f2", "LOW"), _p("f2", "LOW"),
    ]
    result = fid_severity_none(problems, {"HIGH"})
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    assert result["f1"] is False, f"f1 has HIGH -> False; got {result['f1']}"
    assert result["f2"] is True, f"f2: only LOW (not in {{HIGH}}) -> True; got {result['f2']}"
    assert isinstance(result["f1"], bool), "Must be bool"


def test_true_when_no_match() -> None:
    """All problems for fid have severity NOT in the set -> True."""
    problems = [_p("f3", "INFO"), _p("f3", "LOW"), _p("f3", "MEDIUM")]
    result = fid_severity_none(problems, {"CRITICAL", "HIGH"})
    assert result["f3"] is True, f"No CRIT/HIGH -> True; got {result.get('f3')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_none([], {"HIGH"}) == {}


def test_multiple_fids_independent() -> None:
    """f4: MEDIUM only (not in {HIGH}) -> True; f5: LOW,HIGH -> False."""
    problems = [
        _p("f4", "MEDIUM"), _p("f4", "MEDIUM"),
        _p("f5", "LOW"), _p("f5", "HIGH"),
    ]
    result = fid_severity_none(problems, {"HIGH"})
    assert result["f4"] is True, f"f4: no HIGH -> True; got {result.get('f4')}"
    assert result["f5"] is False, f"f5 has HIGH -> False; got {result.get('f5')}"


def test_empty_severity_set_all_true() -> None:
    """Empty severity set -> all True."""
    problems = [_p("f6", "HIGH"), _p("f7", "CRITICAL")]
    result = fid_severity_none(problems, set())
    assert result["f6"] is True
    assert result["f7"] is True
