"""Item 587: fids_by_severity() -- group fid names by dominant severity (2026-06-08).

``fids_by_severity(problems) -> dict[str, set[str]]``:
Returns {severity: {fid, ...}} for ALL dominant severities.
FID-axis complement of classes_by_severity.
Ties: fid appears in ALL tied severity buckets.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: outer dict keyed by SEVERITY; inner set contains FID names (not class names).
     One class, two fids with different dominant severities: severity buckets contain fid names.
     classes_by_severity would put class names in the inner set; fids_by_severity puts fid names.
     Kills impl reusing classes_by_severity on wrong axis.
  2. Dominant severity determines bucket membership (highest count per fid).
     fid 'fx' with 3 HIGH + 1 LOW -> fx only in result['HIGH'] (not in result['LOW']).
     Kills impl putting all severities in all buckets.
  3. Ties: fid with equal max-count severities appears in ALL tied buckets.
     fid 'ft' with 2 HIGH + 2 LOW -> ft in both result['HIGH'] and result['LOW'].
     Kills impl that picks only one severity for tied fids.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Inner container is set[str] (not list[str]).
     Kills impl returning a list instead of a set.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fids_by_severity


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_outer_keyed_by_severity_inner_set_of_fids_primary_discriminator() -> None:
    """PRIMARY DISC.: outer dict keyed by SEVERITY; inner set contains FID names.

    Two fids with different dominant severities:
    'fa' dominated by HIGH -> result['HIGH'] contains 'fa'.
    'fb' dominated by LOW  -> result['LOW']  contains 'fb'.
    classes_by_severity would put class names in the inner set.
    Kills impl reusing classes_by_severity on wrong axis.
    """
    problems = [
        _p("A", "fa", "HIGH"),
        _p("B", "fa", "HIGH"),  # fa: 2 HIGH
        _p("C", "fb", "LOW"),  # fb: 1 LOW
    ]
    result = fids_by_severity(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "HIGH" in result, f"Severity 'HIGH' must be a key; got {list(result)}"
    assert "LOW" in result, f"Severity 'LOW' must be a key; got {list(result)}"
    assert "fa" in result["HIGH"], (
        f"'fa' (dominant HIGH) must be in result['HIGH']; got {result['HIGH']} "
        f"(class name 'A'/'B'/'C' present = class axis wrong)"
    )
    assert "fb" in result["LOW"], (
        f"'fb' (dominant LOW) must be in result['LOW']; got {result['LOW']}"
    )
    assert "A" not in result["HIGH"], (
        "Inner set must contain fid names not class names; 'A' found in result['HIGH']"
    )


def test_dominant_severity_only_not_all_severities() -> None:
    """Only the dominant severity bucket gets the fid.

    fid 'fx' has 3 HIGH and 1 LOW: fx belongs ONLY in result['HIGH'] (not result['LOW']).
    Kills impl that puts all severities in all buckets regardless of counts.
    """
    problems = [
        _p("A", "fx", "HIGH"),
        _p("B", "fx", "HIGH"),
        _p("C", "fx", "HIGH"),
        _p("D", "fx", "LOW"),
    ]
    result = fids_by_severity(problems)
    assert "HIGH" in result, f"Severity 'HIGH' must be a key; got {list(result)}"
    assert "fx" in result["HIGH"], "'fx' dominated by HIGH must be in result['HIGH']"
    if "LOW" in result:
        assert "fx" not in result["LOW"], (
            f"'fx' must NOT be in result['LOW'] (LOW is non-dominant for fx); "
            f"got result['LOW']={result.get('LOW')}"
        )


def test_ties_appear_in_all_tied_buckets() -> None:
    """Tied max-count severities: fid appears in ALL tied severity buckets.

    fid 'ft' has 2 HIGH + 2 LOW -> ft must appear in BOTH result['HIGH'] and result['LOW'].
    Kills impl that arbitrarily picks only one severity for tied fids.
    """
    problems = [
        _p("A", "ft", "HIGH"),
        _p("B", "ft", "HIGH"),
        _p("C", "ft", "LOW"),
        _p("D", "ft", "LOW"),
    ]
    result = fids_by_severity(problems)
    assert "HIGH" in result, f"Severity 'HIGH' must be a key in tie case; got {list(result)}"
    assert "LOW" in result, f"Severity 'LOW' must be a key in tie case; got {list(result)}"
    assert "ft" in result["HIGH"], f"Tied fid 'ft' must be in result['HIGH']; got {result['HIGH']}"
    assert "ft" in result["LOW"], f"Tied fid 'ft' must be in result['LOW']; got {result['LOW']}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = fids_by_severity([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_inner_values_are_sets_not_lists() -> None:
    """Inner container is set[str] (not list[str] or frozenset).

    Kills impl returning lists where sets are required.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "LOW")]
    result = fids_by_severity(problems)
    for sev, fid_group in result.items():
        assert isinstance(fid_group, set), (
            f"Inner value for '{sev}' must be set; got {type(fid_group).__name__}"
        )
