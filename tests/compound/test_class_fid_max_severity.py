"""Item 668: class_fid_max_severity() -- most severe label per class x fid cell.

Returns {class: {fid: max_severity_str}} where severity order is:
CRITICAL > HIGH > MEDIUM > LOW > INFO (unknown severity treated as lowest).
str.  Sparse like class_fid_problem_count_map.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_fid_max_severity


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_max_not_count_not_mode_primary_discriminator() -> None:
    """PRIMARY DISC.: returns MAX severity label (NOT count, NOT most-common).

    Class A, fid 'f1': HIGH,HIGH,LOW -> max='HIGH' (not count=3, not 'LOW').
    Kills count impl; kills mode/frequency impl (HIGH appears most but LOW is not max).
    Actually HIGH IS max in HIGH,HIGH,LOW — so test a case where mode \!= max:
    Class A, fid 'f1': LOW,LOW,LOW,CRITICAL -> mode='LOW' but max='CRITICAL'.
    """
    problems = [_p("A", "f1", "LOW")] * 3 + [_p("A", "f1", "CRITICAL")]
    result = class_fid_max_severity(problems)
    assert isinstance(result, dict), "Outer must be dict"
    assert "A" in result, f"Class 'A' outer key; got {list(result)}"
    assert "f1" in result["A"], f"fid 'f1' inner key; got {list(result['A'])}"
    assert result["A"]["f1"] == "CRITICAL", (
        f"LOW,LOW,LOW,CRITICAL -> max='CRITICAL'; got {result['A']['f1']} "
        f"(mode='LOW' wrong, count=4 wrong)"
    )
    assert isinstance(result["A"]["f1"], str), "Must be str"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_fid_max_severity([]) == {}


def test_single_problem_max_is_itself() -> None:
    """Single problem -> max = its own severity."""
    problems = [_p("A", "f2", "MEDIUM")]
    result = class_fid_max_severity(problems)
    assert result["A"]["f2"] == "MEDIUM", f"Single MEDIUM -> max='MEDIUM'; got {result['A'].get('f2')}"


def test_severity_ordering_critical_beats_high() -> None:
    """CRITICAL beats HIGH even with fewer occurrences."""
    problems = [_p("X", "f3", "HIGH")] * 5 + [_p("X", "f3", "CRITICAL")]
    result = class_fid_max_severity(problems)
    assert result["X"]["f3"] == "CRITICAL", (
        f"5 HIGH + 1 CRIT -> max='CRITICAL'; got {result['X'].get('f3')}"
    )


def test_multiple_cells_independent_maxima() -> None:
    """Different class/fid cells get independent max severity."""
    problems = (
        [_p("A", "f4", "LOW")] * 4 + [_p("A", "f4", "HIGH")]
        + [_p("B", "f5", "INFO")] * 3 + [_p("B", "f5", "MEDIUM")]
    )
    result = class_fid_max_severity(problems)
    assert result["A"]["f4"] == "HIGH", f"A/f4: max='HIGH'; got {result.get('A', {}).get('f4')}"
    assert result["B"]["f5"] == "MEDIUM", f"B/f5: max='MEDIUM'; got {result.get('B', {}).get('f5')}"
