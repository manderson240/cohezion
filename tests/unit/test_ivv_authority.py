"""Unit tests for the IV&V Cryptographic Authority System."""

import hashlib
import tempfile
from pathlib import Path

import pytest

from cohezion.compound.ivv_authority import (
    IVVAuthority,
    IVVAuthorityService,
    IVVKeyManager,
    VerificationRequest,
)


def test_ivv_key_manager_creation_and_perms():
    """Verify that IVVKeyManager initializes with 0600 permissions and valid 256-bit key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        key_file = Path(tmpdir) / "ivv_authority.key"
        km = IVVKeyManager(key_path=key_file)
        assert key_file.exists()
        assert len(km.key) == 32
        mode = key_file.stat().st_mode & 0o777
        assert mode == 0o600

        sig = km.sign(b"test-payload")
        assert km.verify(b"test-payload", sig) is True
        assert km.verify(b"tampered-payload", sig) is False


def test_ivv_authority_independence_enforcement():
    """Verify that the Two-Party Rule strictly prohibits self-certification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        key_file = Path(tmpdir) / "ivv_authority.key"
        store_dir = Path(tmpdir) / "assertions"
        km = IVVKeyManager(key_path=key_file)
        auth = IVVAuthority(key_manager=km, store_dir=store_dir)

        # Creator cannot be verifier
        with pytest.raises(ValueError, match="Independence violation"):
            auth.sign_assertion(
                artifact_hash="hash1",
                test_suite_hash="hash2",
                creator_id="agent-alpha",
                verifier_id="agent-alpha",
                competition="arc_prize_2026",
                passed=True,
            )


def test_ivv_authority_sign_and_verify_cycle():
    """Verify the end-to-end cryptographic signing and verification cycle."""
    with tempfile.TemporaryDirectory() as tmpdir:
        key_file = Path(tmpdir) / "ivv_authority.key"
        store_dir = Path(tmpdir) / "assertions"
        km = IVVKeyManager(key_path=key_file)
        auth = IVVAuthority(key_manager=km, store_dir=store_dir)

        # Create temporary artifact
        artifact = Path(tmpdir) / "solution.py"
        artifact.write_text("def solve(): return 42\n")
        artifact_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()

        assertion = auth.sign_assertion(
            artifact_hash=artifact_hash,
            test_suite_hash="test_suite_sha256",
            creator_id="creator-agent",
            verifier_id="verifier-agent",
            competition="arc_prize_2026",
            passed=True,
        )

        # 1. Successful verification
        valid, reason = auth.verify_assertion(assertion, str(artifact))
        assert valid is True
        assert "passed" in reason

        # 2. Persistence test
        saved_path = auth.save_assertion(assertion)
        assert saved_path.exists()
        loaded = auth.load_assertion(artifact_hash)
        assert loaded is not None
        assert loaded.signature == assertion.signature

        # 3. Tampered artifact fails verification immediately
        artifact.write_text("def solve(): return 0\n")
        valid, reason = auth.verify_assertion(assertion, str(artifact))
        assert valid is False
        assert "Artifact hash mismatch" in reason


def test_ivv_service_anti_spoofing():
    """Verify IVVAuthorityService rejects attempts by creators to impersonate verifiers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        key_file = Path(tmpdir) / "ivv_authority.key"
        store_dir = Path(tmpdir) / "assertions"
        km = IVVKeyManager(key_path=key_file)
        auth = IVVAuthority(key_manager=km, store_dir=store_dir)
        service = IVVAuthorityService(authority=auth, verifier_id="authority-verifier")

        artifact = Path(tmpdir) / "solution.py"
        artifact.write_text("x = 1\n")

        # Spoof attempt: creator passes verifier's identity
        req = VerificationRequest(
            artifact_path=str(artifact),
            competition="arc_prize_2026",
            creator_id="authority-verifier",
        )
        assertion = service.verify_request(req)
        assert assertion.passed is False
        assert any(f.gate == "INDEPENDENCE_CHECK" for f in assertion.findings)


def test_ivv_service_data_artifact_verification():
    """Verify IVVAuthorityService audits tabular CSV and data artifacts without AST parse errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        key_file = Path(tmpdir) / "ivv_authority.key"
        store_dir = Path(tmpdir) / "assertions"
        km = IVVKeyManager(key_path=key_file)
        auth = IVVAuthority(key_manager=km, store_dir=store_dir)
        service = IVVAuthorityService(authority=auth, verifier_id="authority-verifier")

        # 1. Valid CSV passes
        csv_file = Path(tmpdir) / "submission.csv"
        csv_file.write_text("id,prediction\n0,1.5\n1,2.0\n")
        req = VerificationRequest(
            artifact_path=str(csv_file),
            competition="biohub_cell_tracking_during_development",
            creator_id="cohezion-agent",
        )
        assertion = service.verify_request(req)
        assert assertion.passed is True
        assert not any(f.gate == "AST_PARSE" for f in assertion.findings)

        # 2. Empty CSV fails
        empty_csv = Path(tmpdir) / "empty.csv"
        empty_csv.write_text("")
        req_empty = VerificationRequest(
            artifact_path=str(empty_csv),
            competition="biohub_cell_tracking_during_development",
            creator_id="cohezion-agent",
        )
        assert service.verify_request(req_empty).passed is False

        # 3. CSV leaking authority key path fails
        leaking_csv = Path(tmpdir) / "leak.csv"
        leaking_csv.write_text("id,key\n0,~/.cohezion/security/ivv_authority.key\n")
        req_leak = VerificationRequest(
            artifact_path=str(leaking_csv),
            competition="biohub_cell_tracking_during_development",
            creator_id="cohezion-agent",
        )
        assertion_leak = service.verify_request(req_leak)
        assert assertion_leak.passed is False
        assert any(f.gate == "SECURITY_BOUNDARY" for f in assertion_leak.findings)
