"""Item 597: fid_top_severity() -- dominant severity label per fid (2026-06-08).

``fid_top_severity(problems) -> dict[str, str]``:
Returns {fid: dominant_severity_label} for each fid.
Dominant = severity with the highest count for that fid.
Ties broken by alphabetically descending severity name (e.g. 'LOW' > 'HIGH').
FID-axis complement of class_top_severity.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed by FID name (not class name).
     fid 'f1' with HIGH x3 and LOW x1 -> result['f1'] == 'HIGH'; 'A' must NOT be a key.
     Kills impl reusing class_top_severity on wrong axis.
  2. Most-frequent label selected per fid.
     fid 'fa' with LOW x4, HIGH x1 -> result['fa'] == 'LOW'.
     Kills impl returning minority or first-seen label.
  3. Tie broken by alphabetically descending label.
     fid 'fx' with HIGH x2, LOW x2 -> 'LOW' > 'HIGH' alpha-desc -> result['fx'] == 'LOW'.
     Kills impl using ascending order (would give 'HIGH').
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Multiple fids each get independent dominant label.
     Kills impl aggregating across all fids.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_top_severity


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by FID name (not class name).

    fid 'f1' has HIGH x3 and LOW x1.  Result must key on 'f1', not 'A'.
    Kills impl reusing class_top_severity on wrong axis.
    """
    problems = [_p("A", "f1", "HIGH")] * 3 + [_p("A", "f1", "LOW")]
    result = fid_top_severity(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, f"fid 'f1' must be in result; got {result}"
    assert "A" not in result, f"Class 'A' must NOT be a key (FID axis required); got {result}"
    assert result["f1"] == "HIGH", f"'HIGH' appears 3x for fid 'f1'; got {result['f1']!r}"


def test_most_frequent_label_wins_per_fid() -> None:
    """Most-frequent severity wins per fid (not minority or first-seen).

    fid 'fa' LOW x4, HIGH x1 -> 'LOW'.
    Kills impl returning the minority or a fixed label.
    """
    problems = [_p("A", "fa", "LOW")] * 4 + [_p("B", "fa", "HIGH")]
    result = fid_top_severity(problems)
    assert result["fa"] == "LOW", f"'LOW' appears 4x for fid 'fa'; got {result['fa']!r}"


def test_ties_broken_by_alphabetically_descending_label() -> None:
    """Ties broken by alphabetically descending severity label (same rule as class_top_severity).

    fid 'fx' HIGH x2, LOW x2 -> 'LOW' > 'HIGH' alpha-desc -> 'LOW'.
    fid 'fy' HIGH x1, MEDIUM x1 -> 'MEDIUM' > 'HIGH' -> 'MEDIUM'.
    Kills impl using ascending order.
    """
    problems_x = [_p("A", "fx", "HIGH")] * 2 + [_p("B", "fx", "LOW")] * 2
    result_x = fid_top_severity(problems_x)
    assert result_x["fx"] == "LOW", (
        f"Tie HIGH=2/LOW=2 for 'fx': 'LOW'>'HIGH' alpha-desc -> 'LOW'; got {result_x['fx']!r}"
    )

    problems_y = [_p("A", "fy", "HIGH"), _p("B", "fy", "MEDIUM")]
    result_y = fid_top_severity(problems_y)
    assert result_y["fy"] == "MEDIUM", (
        f"Tie HIGH=1/MEDIUM=1 for 'fy': 'MEDIUM'>'HIGH' alpha-desc -> 'MEDIUM'; got {result_y['fy']!r}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise)."""
    result = fid_top_severity([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_multiple_fids_independent() -> None:
    """Multiple fids each get their own dominant label independently.

    Kills impl aggregating across all fids or returning a single value.
    """
    problems = (
        [_p("A", "f1", "CRITICAL")] * 5
        + [_p("A", "f1", "LOW")]
        + [_p("B", "f2", "HIGH")] * 4
        + [_p("C", "f2", "MEDIUM")] * 2
    )
    result = fid_top_severity(problems)
    assert "f1" in result and "f2" in result, f"Both fids must be present; got {list(result)}"
    assert result["f1"] == "CRITICAL", f"fid f1 dominant is CRITICAL (5 vs 1); got {result['f1']!r}"
    assert result["f2"] == "HIGH", f"fid f2 dominant is HIGH (4 vs 2); got {result['f2']!r}"
