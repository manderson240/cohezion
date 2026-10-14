"""Unit tests for the Independent Verification & Validation (IV&V) Engine."""

import pytest
from cohezion.compound.ivv_engine import (
    IndependentVerifier,
    IVVGatekeeper,
    IVVSeverity,
)


def test_ivv_blocks_self_certification():
    """Verify that a creator CANNOT certify their own code."""
    verifier = IndependentVerifier(verifier_id="agent-creator-42")
    cert = verifier.audit_code_artifact(
        artifact_id="kernel_v15.py",
        creator_id="agent-creator-42",  # SAME ID!
        code_str="print('hello')",
        requirements_spec={},
    )

    assert cert.passed is False
    assert cert.is_valid is False
    assert any("Creator attempted to act as verifier" in f.description for f in cert.findings)


def test_ivv_approves_valid_independent_code():
    """Verify that an independent verifier can approve sound code."""
    verifier = IndependentVerifier(verifier_id="adversarial-verifier-99")
    code = """
import numpy as np
def predict(df):
    sub = ['ACL', 'Meniscus']
    df['Abnormal'] = np.maximum(df['Abnormal'], df[sub].max(axis=1))
    return df
"""
    cert = verifier.audit_code_artifact(
        artifact_id="rsna_monotonic_v25.py",
        creator_id="code-creator-11",
        code_str=code,
        requirements_spec={"competition_type": "rsna-knee"},
    )

    assert cert.passed is True
    assert cert.is_valid is True
    assert cert.creator_id != cert.verifier_id
    assert cert.signature != ""


def test_ivv_flags_kolmogorov_monotonicity_violation():
    """Verify independent verifier catches missing Kolmogorov monotonicity in RSNA Knee."""
    verifier = IndependentVerifier(verifier_id="adversarial-verifier-99")
    non_monotonic_code = """
def predict(df):
    # Missing np.maximum or Kolmogorov projection
    df['Abnormal'] = df['raw_abnormal'] * 0.9
    df['ACL'] = df['raw_acl']
    return df
"""
    cert = verifier.audit_code_artifact(
        artifact_id="rsna_flawed_v26.py",
        creator_id="code-creator-11",
        code_str=non_monotonic_code,
        requirements_spec={"competition_type": "rsna-knee"},
    )

    assert cert.passed is False
    assert any("Kolmogorov projection" in f.description for f in cert.findings)


def test_ivv_gatekeeper_enforcement():
    """Verify IVVGatekeeper blocks unverified and self-certified deployments."""
    gatekeeper = IVVGatekeeper()
    verifier = IndependentVerifier(verifier_id="independent-verifier-01")

    # 1. Block deployment with no certificate
    allowed, reason = gatekeeper.verify_deployment_readiness("unverified_kernel.py", "creator-A")
    assert allowed is False
    assert "has NO Independent Verification Certificate" in reason

    # 2. Register valid certificate
    valid_code = "x = 1 + 1"
    cert = verifier.audit_code_artifact(
        artifact_id="clean_kernel.py",
        creator_id="creator-A",
        code_str=valid_code,
        requirements_spec={},
    )
    gatekeeper.register_certificate(cert)

    allowed, reason = gatekeeper.verify_deployment_readiness("clean_kernel.py", "creator-A")
    assert allowed is True
    assert "DEPLOYMENT APPROVED" in reason

    # 3. Block if creator ID does not match
    allowed_wrong, reason_wrong = gatekeeper.verify_deployment_readiness("clean_kernel.py", "imposter-B")
    assert allowed_wrong is False
    assert "Creator ID mismatch" in reason_wrong
