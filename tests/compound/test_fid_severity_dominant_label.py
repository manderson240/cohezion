"""Item 719: fid_severity_dominant_label() -- single most-common severity per fid.

fid_severity_dominant_label(problems) -> dict[str, str].
Fid-axis complement of class_severity_dominant_label (item 718).
Returns {fid: label}; ties broken by min(label) alphabetically.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND returns single str (not frozenset);
     fid 'f1': LOW×3+HIGH×2 -> 'LOW'; class-outer gives key='A' wrong;
     frozenset-impl gives {'LOW'} wrong.
  2. Tie broken alphabetically: fid 'f2': HIGH×2+LOW×2 -> 'HIGH'.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is str.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_dominant_label


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_single_label_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND returns single str label.

    fid 'f1': LOW×3 + HIGH×2 -> 'LOW'.
    class-outer gives key='A' wrong; frozenset-impl gives {'LOW'} wrong.
    """
    problems = [
        _p("f1", "LOW"),
        _p("f1", "LOW"),
        _p("f1", "LOW"),
        _p("f1", "HIGH"),
        _p("f1", "HIGH"),
    ]
    result = fid_severity_dominant_label(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == "LOW", f"LOW×3 > HIGH×2 -> 'LOW'; got {result['f1']!r}"
    assert isinstance(result["f1"], str), f"Must be str; got {type(result['f1'])}"


def test_tie_broken_alphabetically() -> None:
    """Tie: min(tied_labels) alphabetically.

    fid 'f2': HIGH×2 + LOW×2 -> 'HIGH' (H < L).
    """
    problems = [_p("f2", "HIGH"), _p("f2", "HIGH"), _p("f2", "LOW"), _p("f2", "LOW")]
    result = fid_severity_dominant_label(problems)
    assert result["f2"] == "HIGH", f"HIGH×2 tie LOW×2 -> 'HIGH'; got {result.get('f2')!r}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_dominant_label([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid computes independently."""
    problems = [_p("f3", "CRITICAL"), _p("f3", "CRITICAL"), _p("f3", "HIGH")]  # f3 -> CRITICAL
    problems += [_p("f4", "INFO"), _p("f4", "LOW"), _p("f4", "LOW")]  # f4 -> LOW
    result = fid_severity_dominant_label(problems)
    assert result["f3"] == "CRITICAL", (
        f"f3: CRIT×2 > HIGH×1 -> 'CRITICAL'; got {result.get('f3')!r}"
    )
    assert result["f4"] == "LOW", f"f4: LOW×2 > INFO×1 -> 'LOW'; got {result.get('f4')!r}"


def test_return_type_is_str() -> None:
    """Result values must be str."""
    problems = [_p("f5", "MEDIUM"), _p("f5", "MEDIUM")]
    result = fid_severity_dominant_label(problems)
    assert isinstance(result["f5"], str), f"Must be str; got {type(result['f5'])}"
    assert result["f5"] == "MEDIUM", f"Only MEDIUM -> 'MEDIUM'; got {result.get('f5')!r}"
