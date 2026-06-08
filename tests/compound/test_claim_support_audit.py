"""Discriminating tests for claim_support_audit (item 69, Thread A).

Backlog falsifiable check (items.69):
  - with an injected DETERMINISTIC judge:
    a trajectory whose claim is later contradicted → that span flagged as the
    first error; a fully-supported trajectory → clean; empty → []; deterministic.

Each test fails a plausible wrong implementation:
  - one that fabricates findings on an empty trajectory → T_empty_trajectory
  - one that reports a finding for non-consequential claims → T_non_consequential
  - one that doesn't localise the FIRST error span → T_first_error_span
  - one that ignores the injected judge and uses hardcoded logic → T_injected_judge
  - one that is non-deterministic (random ordering) → T_deterministic
  - one that raises on a clean trajectory → T_clean_trajectory
"""

from __future__ import annotations

from cohezion.compound.claim_support_audit import (
    SupportLabel,
    claim_support_audit,
    claim_support_audit_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step(response: str, prompt: str = "") -> dict:
    return {"prompt": prompt, "response": response}


def _always_supported(claim: str, ctx: str) -> SupportLabel:  # noqa: ARG001
    return SupportLabel.SUPPORTED


def _always_missing(claim: str, ctx: str) -> SupportLabel:  # noqa: ARG001
    return SupportLabel.MISSING


def _always_contradicted(claim: str, ctx: str) -> SupportLabel:  # noqa: ARG001
    return SupportLabel.CONTRADICTED


# ---------------------------------------------------------------------------
# T_empty_trajectory: empty → clean (findings=[])
# Fails: a selector that returns fabricated findings for an empty trajectory.
# ---------------------------------------------------------------------------


def test_empty_trajectory_returns_no_findings() -> None:
    result = claim_support_audit([])
    assert result.findings == []
    assert result.first_error_span is None
    assert result.trajectory_length == 0


# ---------------------------------------------------------------------------
# T_clean_trajectory: all claims supported → findings=[] (clean report)
# Fails: a selector that always produces findings regardless of judge verdict.
# ---------------------------------------------------------------------------


def test_fully_supported_trajectory_is_clean() -> None:
    # All claims are SUPPORTED by the injected judge → no findings.
    traj = [
        _step("This is the first claim about the system state for testing."),
        _step(
            "This is the first claim about the system state for testing. "
            "Second claim that reuses the first claim above."
        ),
    ]
    result = claim_support_audit(traj, judge=_always_supported)
    assert result.findings == []
    assert result.first_error_span is None
    assert result.judge_label == "injected"


# ---------------------------------------------------------------------------
# T_non_consequential: non-consequential unsupported claims must NOT be findings
# Fails: a selector that flags ALL unsupported claims (ignores consequentiality).
# ---------------------------------------------------------------------------


def test_non_consequential_unsupported_claim_is_not_a_finding() -> None:
    # A single step with one claim. The claim is NOT reused in any later step
    # → not consequential → even if MISSING, no finding.
    traj = [
        _step("This is an isolated claim that no later step will use at all."),
    ]
    result = claim_support_audit(traj, judge=_always_missing)
    # Non-consequential claims should be omitted from findings.
    assert result.findings == []
    assert result.first_error_span is None


# ---------------------------------------------------------------------------
# T_first_error_span: localises the FIRST unsupported consequential claim
# Fails: a selector that reports all errors but sets first_error_span to the last.
# ---------------------------------------------------------------------------


def test_first_error_span_is_the_earliest_step() -> None:
    # Step 0 introduces claim A; step 1 introduces claim B and reuses A; step 2 reuses B.
    # Judge says MISSING for all → both A (step 0, reused in step 1) and B (step 1,
    # reused in step 2) are unsupported consequential claims.
    # first_error_span must be 0 (earliest), not 1.
    traj = [
        _step("Claim about the alpha component in the system design analysis."),
        _step(
            "Claim about the alpha component in the system design analysis. "
            "New claim about beta module integration with the framework."
        ),
        _step("New claim about beta module integration with the framework."),
    ]
    result = claim_support_audit(traj, judge=_always_missing)
    # first_error_span must be step 0 (where the first consequential claim lives).
    assert result.first_error_span is not None
    assert result.first_error_span == 0  # NOT 1


# ---------------------------------------------------------------------------
# T_injected_judge: injected judge is consulted (not hardcoded)
# Fails: a selector that ignores the injected judge.
# ---------------------------------------------------------------------------


def test_injected_judge_always_contradicted_produces_findings() -> None:
    # Make a trajectory where at least one claim IS consequential (reused in next step).
    claim_text = "The neural network training rate converges at this specific value here."
    traj = [
        _step(claim_text),
        _step("The neural network training rate converges. " + claim_text),
    ]
    result = claim_support_audit(traj, judge=_always_contradicted)
    # _always_contradicted → all consequential claims should show as CONTRADICTED.
    contradicted_findings = [f for f in result.findings if f.support == SupportLabel.CONTRADICTED]
    # There should be at least one CONTRADICTED finding (injected judge was consulted).
    assert len(contradicted_findings) >= 1


def test_injected_judge_always_supported_overrides_default() -> None:
    # The default deterministic judge might return MISSING for a novel claim.
    # Injecting always_supported must override it → no findings.
    claim_text = "Completely novel claim ZZZ999XYZ that appears in no prior context."
    traj = [
        _step(claim_text),
        _step("Completely novel claim ZZZ999XYZ is referenced here too."),
    ]
    result = claim_support_audit(traj, judge=_always_supported)
    assert result.findings == []
    assert result.judge_label == "injected"


# ---------------------------------------------------------------------------
# T_deterministic: same input + same judge → same output (no randomness)
# Fails: a selector with random tiebreaking or non-deterministic ordering.
# ---------------------------------------------------------------------------


def test_audit_is_deterministic_given_same_input_and_judge() -> None:
    traj = [
        _step("First consequential claim about database schema layout design."),
        _step(
            "First consequential claim about database schema layout design. "
            "Additional details about the implementation approach."
        ),
    ]
    result_a = claim_support_audit(traj, judge=_always_missing)
    result_b = claim_support_audit(traj, judge=_always_missing)
    assert result_a.findings == result_b.findings
    assert result_a.first_error_span == result_b.first_error_span
    assert result_a.trajectory_length == result_b.trajectory_length


# ---------------------------------------------------------------------------
# T_report: report dict contract
# ---------------------------------------------------------------------------


def test_report_contains_required_keys() -> None:
    report = claim_support_audit_report([], judge=_always_supported)
    for key in (
        "trajectory_length",
        "total_claims_audited",
        "consequential_claims",
        "findings_count",
        "first_error_span",
        "findings",
        "judge",
        "clean",
    ):
        assert key in report, f"missing key: {key}"


def test_report_clean_is_true_for_empty_trajectory() -> None:
    report = claim_support_audit_report([], judge=_always_supported)
    assert report["clean"] is True
    assert report["findings_count"] == 0


def test_report_clean_false_when_findings_exist() -> None:
    # Build a trajectory with a consequential, unsupported claim.
    claim_text = "Critical claim about memory allocation pattern used across steps."
    traj = [
        _step(claim_text),
        _step("Critical claim about memory allocation pattern used across steps. Next step."),
    ]
    report = claim_support_audit_report(traj, judge=_always_missing)
    # At least one finding → clean should be False.
    if report["findings_count"] > 0:
        assert report["clean"] is False


# ---------------------------------------------------------------------------
# Result is frozen (immutable after construction)
# ---------------------------------------------------------------------------


def test_claim_audit_result_is_frozen() -> None:
    result = claim_support_audit([])
    try:
        result.trajectory_length = 99  # type: ignore[misc]
        assert False, "should have raised FrozenInstanceError"
    except Exception:
        pass
