"""Unit tests for Local Adversarial Auditor."""

from cohezion.verification.local_adversarial_auditor import LocalAdversarialAuditor


def test_local_adversarial_audit_deflation() -> None:
    auditor = LocalAdversarialAuditor()
    report = auditor.audit_artifact_claims(
        artifact_id="test_artifact",
        claimed_score=0.95,
        claimed_summary="Inflated claim test",
    )

    assert report.artifact_id == "test_artifact"
    assert report.raw_claimed_score == 0.95
    assert report.deflated_adversarial_score < 0.95
    assert report.total_penalty > 0.0
    assert len(report.perspectives) == 3
