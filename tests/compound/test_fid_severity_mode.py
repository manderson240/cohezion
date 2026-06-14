"""Item 599: fid_severity_mode() -- full co-dominant severity set per fid (2026-06-08).

``fid_severity_mode(problems) -> dict[str, frozenset[str]]``:
Returns {fid: frozenset_of_dominant_severity_labels} where dominant labels
are ALL severities sharing the maximum count for that fid.
FID-axis complement of class_severity_mode.
Single dominant -> singleton frozenset.  Tied -> frozenset of size > 1.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: outer dict keyed by FID (not class name).
     class_severity_mode gives {'A': frozenset({'HIGH'})} (class axis wrong).
     Kills impl reusing class_severity_mode on wrong axis.
  2. ALL co-dominant labels returned (not just one).
     fid 'fx': HIGH x2, LOW x2 -> frozenset({'HIGH','LOW'}) not just 'HIGH' or 'LOW'.
     Kills impl returning single label (like fid_top_severity).
  3. Only MAX-count labels included; minority labels excluded.
     fid 'fx': HIGH x3, LOW x1 -> frozenset({'HIGH'}) (not frozenset({'HIGH','LOW'})).
     Kills impl returning ALL severities not just dominant ones.
  4. Return type is frozenset (not set or list).
     Kills impl using mutable set or list.
  5. Empty -> {} (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_mode


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_outer_keyed_by_fid_not_class_primary_discriminator() -> None:
    """PRIMARY DISC.: outer dict keyed by FID (not class name).

    fid 'f1' with HIGH x3 from classes A, B, C:
    result key must be 'f1', NOT 'A', 'B', or 'C'.
    class_severity_mode would give {'A': ..., 'B': ..., 'C': ...} (class axis).
    Kills impl reusing class_severity_mode on wrong axis.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f1", "HIGH"), _p("C", "f1", "HIGH")]
    result = fid_severity_mode(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, (
        f"Result must be keyed by fid 'f1'; got keys={list(result)} "
        f"(class names = class axis wrong)"
    )
    assert "A" not in result, f"Class 'A' must NOT be a key; got {result}"
    assert result["f1"] == frozenset({"HIGH"}), (
        f"All HIGH -> frozenset({{'HIGH'}}); got {result['f1']}"
    )


def test_all_co_dominant_labels_returned_not_just_one() -> None:
    """ALL co-dominant labels returned in frozenset (not just the first or max-alpha).

    fid 'fx': HIGH x2, LOW x2 -> frozenset({'HIGH', 'LOW'}).
    fid_top_severity would return only 'LOW' (single label, alpha-desc tie-break).
    Kills impl returning a single label on ties.
    """
    problems = [_p("A", "fx", "HIGH")] * 2 + [_p("B", "fx", "LOW")] * 2
    result = fid_severity_mode(problems)
    assert result["fx"] == frozenset({"HIGH", "LOW"}), (
        f"Tie HIGH=2/LOW=2 -> frozenset({{'HIGH','LOW'}}); got {result['fx']}"
    )
    assert len(result["fx"]) == 2, f"Both tied labels must be in frozenset; got {result['fx']}"


def test_only_max_count_labels_included_not_all() -> None:
    """Only majority-count labels included; minority labels are excluded.

    fid 'fx': HIGH x3, LOW x1 -> frozenset({'HIGH'}) not frozenset({'HIGH','LOW'}).
    Kills impl returning ALL severities regardless of count.
    """
    problems = [_p("A", "fx", "HIGH")] * 3 + [_p("B", "fx", "LOW")]
    result = fid_severity_mode(problems)
    assert result["fx"] == frozenset({"HIGH"}), (
        f"HIGH=3 > LOW=1 -> frozenset({{'HIGH'}}); got {result['fx']} "
        f"(including LOW = returning all labels, not just dominant)"
    )
    assert "LOW" not in result["fx"], f"LOW must be excluded (minority label); got {result['fx']}"


def test_values_are_frozenset_not_set_or_list() -> None:
    """Return type is frozenset (not mutable set or list).

    Kills impl using set() or list() instead of frozenset().
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f1", "CRITICAL")]
    result = fid_severity_mode(problems)
    for fid, mode_set in result.items():
        assert isinstance(mode_set, frozenset), (
            "Value for fid " + repr(fid) + " must be frozenset; got " + type(mode_set).__name__
        )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = fid_severity_mode([])
    assert result == {}, f"Empty -> {{}}; got {result}"
