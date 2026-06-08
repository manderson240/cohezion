"""Item 612: fid_severity_entropy() -- Shannon entropy of severity distribution per fid.

FID-axis complement of class_severity_entropy (item 260).
``fid_severity_entropy(problems, fid) -> float``
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_entropy


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid (not class).

    fid 'f1' with HIGH=1, LOW=1: H=1.0.
    If impl uses p.problem_class instead of p.finding_id it would bucket wrong.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f1", "LOW")]
    result = fid_severity_entropy(problems, "f1")
    assert abs(result - 1.0) < 1e-9, (
        "fid 'f1' HIGH=1, LOW=1: H=1.0 bit; got " + repr(result)
    )


def test_unlabelled_excluded_from_distribution() -> None:
    """Unlabelled (severity='') excluded from distribution.

    1 HIGH + 1 unlabelled for fid 'f1':
    labelled-only -> single severity HIGH -> H=0.0.
    If unlabelled included: HIGH=0.5, NONE=0.5 -> H=1.0. Must return 0.0.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        Problem(problem_class="A", finding_id="f1"),  # severity=""
    ]
    result = fid_severity_entropy(problems, "f1")
    assert result == 0.0, (
        "1 HIGH + 1 unlabelled -> only HIGH labelled -> H=0.0; got " + repr(result)
    )


def test_zero_for_single_severity() -> None:
    """Single labelled severity -> H=0.0."""
    problems = [_p("A", "f1", "CRITICAL")] * 5
    result = fid_severity_entropy(problems, "f1")
    assert result == 0.0, "Single severity -> H=0.0; got " + repr(result)


def test_one_bit_for_uniform_two_label() -> None:
    """Uniform 2-severity -> H=1.0 bit (not 0.5 Gini)."""
    problems = [_p("A", "f1", "HIGH"), _p("B", "f1", "LOW")]
    result = fid_severity_entropy(problems, "f1")
    assert abs(result - 1.0) < 1e-9, (
        "Uniform 2-label -> H=1.0; got " + repr(result)
    )


def test_zero_for_unknown_fid_or_empty() -> None:
    """0.0 for unknown fid or empty input (no raise)."""
    assert fid_severity_entropy([], "f1") == 0.0, "Empty -> 0.0"
    problems = [_p("A", "f1", "HIGH")]
    assert fid_severity_entropy(problems, "unknown") == 0.0, "Unknown fid -> 0.0"
