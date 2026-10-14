"""Unit tests for the IV&V Cryptographic Authority System."""

import hashlib
import tempfile
from pathlib import Path
import pytest
from cohezion.compound.ivv_authority import (
    IVVAuthority,
    IVVAuthorityService,
    IVVFinding,
    IVVKeyManager,
    IVVSeverity,
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
