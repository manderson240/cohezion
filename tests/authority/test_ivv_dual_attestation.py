"""Unit tests for Cohezion Two-Party Cryptographic IV&V Authority & Dual Attestation."""

import tempfile
from pathlib import Path
import pytest

from cohezion.authority.ivv import (
    CreatorAttestation,
    DualAttestation,
    IVVPolicy,
    PromotionGatekeeper,
    TransparencyLog,
    VerifierAttestation,
)
from cohezion.compound.ivv_authority import IVVKeyManager


def test_dual_attestation_blocks_self_verification():
    """Verify that creator_id == verifier_id raises an independence violation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        key_file = Path(tmpdir) / "ivv.key"
        artifact = Path(tmpdir) / "model_weights.bin"
        artifact.write_bytes(b"model-weights-v1")
        evidence = Path(tmpdir) / "test_report.json"
        evidence.write_bytes(b"{\"passed\": true}")

        km = IVVKeyManager(key_path=key_file)
        policy = IVVPolicy(key_manager=km)

        creator_att = policy.create_creator_attestation(
            artifact_path=artifact,
            creator_id="alice-creator",
            claim="SOTA Model v1",
        )

        # Alice attempts to verify her own work
        verifier_att = policy.create_verifier_attestation(
            artifact_path=artifact,
            verifier_id="alice-creator",  # Self-verification attempt
            verdict=True,
            evidence_path=evidence,
            nonce=creator_att.nonce,
        )

        with pytest.raises(ValueError, match="Independence Violation"):
            policy.assemble_dual_attestation(creator_att, verifier_att)


def test_dual_attestation_success_and_transparency_log():
    """Verify valid dual attestation signing, log appending, and tamper-detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        key_file = Path(tmpdir) / "ivv.key"
        log_file = Path(tmpdir) / "transparency_log.jsonl"
        artifact = Path(tmpdir) / "kernel_submission.ipynb"
        artifact.write_bytes(b"notebook_code_content_v1")
        evidence = Path(tmpdir) / "test_report.json"
        evidence.write_bytes(b"{\"tests\": 25, \"passed\": 25}")

        km = IVVKeyManager(key_path=key_file)
        policy = IVVPolicy(key_manager=km)
        tlog = TransparencyLog(log_path=log_file)
        gatekeeper = PromotionGatekeeper(policy=policy, transparency_log=tlog)

        creator_att = policy.create_creator_attestation(
            artifact_path=artifact,
            creator_id="alice-creator",
            claim="RSNA SOTA Ensemble v29",
        )

        verifier_att = policy.create_verifier_attestation(
            artifact_path=artifact,
            verifier_id="bob-independent-verifier",
            verdict=True,
            evidence_path=evidence,
            nonce=creator_att.nonce,
        )

        da = gatekeeper.certify_and_promote(artifact, creator_att, verifier_att)
        assert da.artifact_digest == creator_att.artifact_digest
        assert da.creator.creator_id == "alice-creator"
        assert da.verifier.verifier_id == "bob-independent-verifier"

        # Verify transparency log integrity
        assert tlog.verify_integrity() is True

        # Assert promotable passes
        gatekeeper.assert_promotable(artifact, da)

        # Tampering with artifact raises error
        artifact.write_bytes(b"tampered_content")
        with pytest.raises(ValueError, match="Artifact modified after attestation"):
            gatekeeper.assert_promotable(artifact, da)
