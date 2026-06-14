"""Item 583: fid_severity_entropies() -- Shannon entropy dict for all fids (2026-06-08).

``fid_severity_entropies(problems) -> dict[str, float]``:
Returns {fid: entropy_bits} for ALL fids.  H = -sum(p*log2(p)).
FID-axis complement of class_severity_entropies.
Empty -> {}.  Single-severity fid -> 0.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     One fid 'f1' in two classes with HIGH and LOW: entropy = 1.0.
     class_severity_entropies would key on class names; fid_severity_entropies keys on fid names.
     Kills impl reusing class_severity_entropies on wrong axis.
  2. Uses log2 (bits) not natural log: uniform 2-severity fid -> 1.0 bit.
     Kills impl using math.log instead of math.log2.
  3. Single-severity fid -> 0.0.
     Kills impl returning non-zero for homogeneous fid.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Returns dict for ALL fids (multiple fids with different entropies).
     Kills impl returning only a subset or a single float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_entropies


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed on FID axis (not class axis).

    fid 'f1' has problems with HIGH and LOW severities -> entropy = 1.0 bit.
    class_severity_entropies({'A': ...}) would key on class; here keys are fid names.
    Kills impl reusing class_severity_entropies on wrong axis.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # f1: 1 HIGH, 1 LOW -> entropy = 1.0
        _p("B", "f1", "LOW"),
    ]
    result = fid_severity_entropies(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, f"fid 'f1' must be in result; got {result}"
    assert "A" not in result, (
        f"Keys must be fid names (not class names); got {result} ('A' present = class axis wrong)"
    )
    assert abs(result["f1"] - 1.0) < 1e-9, f"f1: uniform 2-severity -> 1.0 bit; got {result['f1']}"


def test_log2_not_natural_log() -> None:
    """Uses log2 (bits) not natural log (nats).

    Uniform 2-severity: H = 1.0 bit.  With natural log: H ~= 0.693 nats.
    Kills impl using math.log instead of math.log2.
    """
    problems = [_p("A", "fa", "HIGH"), _p("B", "fa", "LOW")]
    result = fid_severity_entropies(problems)
    assert abs(result["fa"] - 1.0) < 1e-9, (
        f"Uniform 2-severity -> 1.0 bit (not 0.693 nat); got {result['fa']}"
    )


def test_single_severity_returns_zero() -> None:
    """Single severity -> 0.0 (minimum entropy).

    Kills impl returning non-zero for a homogeneous fid.
    """
    problems = [_p(f"class{i}", "f_mono", "HIGH") for i in range(4)]
    result = fid_severity_entropies(problems)
    assert abs(result["f_mono"]) < 1e-9, f"All-HIGH fid -> 0.0; got {result['f_mono']}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = fid_severity_entropies([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_multiple_fids_all_present() -> None:
    """Returns dict with entry for EVERY fid.

    Kills impl returning only a single float or a partial dict.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # f1: single severity -> 0.0
        _p("B", "f2", "HIGH"),  # f2: two severities -> 1.0 bit
        _p("C", "f2", "LOW"),
    ]
    result = fid_severity_entropies(problems)
    assert "f1" in result and "f2" in result, f"Both fids must appear; got {result}"
    assert abs(result["f1"]) < 1e-9, f"f1 single severity -> 0.0; got {result['f1']}"
    assert abs(result["f2"] - 1.0) < 1e-9, f"f2 uniform 2-sev -> 1.0; got {result['f2']}"
