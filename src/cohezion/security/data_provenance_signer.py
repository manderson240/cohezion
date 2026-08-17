r"""Cryptographic Data Provenance & SHA-256 Signer (Remediation 3)
===================================================================
Signs and verifies all fine-tuning dataset samples with SHA-256 HMAC signatures
to prevent data poisoning, tampering, or malicious trajectory injections.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

import hmac
import os

SECRET_PROVENANCE_KEY = os.environ.get("COHEZION_PROVENANCE_KEY", "cohezion_sovereign_agi_provenance_key_2026").encode("utf-8")
_KEY_RING: dict[str, bytes] = {
    "v1": SECRET_PROVENANCE_KEY,
    "v2": b"cohezion_sovereign_agi_provenance_key_v2_2026_rotated",
}
_ACTIVE_KEY_ID = "v2"


class DataProvenanceSigner:
    """Cryptographic SHA-256 HMAC provenance signer with key rotation support."""

    @staticmethod
    def sign_sample(sample: dict[str, Any], key_id: str = _ACTIVE_KEY_ID) -> str:
        """Computes HMAC-SHA256 signature for a dataset sample with key version prefix."""
        key = _KEY_RING.get(key_id, SECRET_PROVENANCE_KEY)
        payload_bytes = json.dumps(sample, sort_keys=True).encode("utf-8")
        sig = hmac.new(key, payload_bytes, hashlib.sha256).hexdigest()
        return f"{key_id}:{sig}"

    @staticmethod
    def verify_sample(sample: dict[str, Any], expected_signature: str) -> bool:
        """Verifies sample SHA-256 HMAC signature against data poisoning attacks."""
        if ":" in expected_signature:
            key_id, raw_sig = expected_signature.split(":", 1)
            key = _KEY_RING.get(key_id, SECRET_PROVENANCE_KEY)
        else:
            key = SECRET_PROVENANCE_KEY
            raw_sig = expected_signature

        payload_bytes = json.dumps(sample, sort_keys=True).encode("utf-8")
        computed_sig = hmac.new(key, payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed_sig, raw_sig)


def main() -> None:
    sample = {"instruction": "Execute safe action", "response": "def action(): pass"}
    sig = DataProvenanceSigner.sign_sample(sample)
    valid = DataProvenanceSigner.verify_sample(sample, sig)

    print("\n" + "=" * 95)
    print("      🔐 COHEZION CRYPTOGRAPHIC DATA PROVENANCE SIGNER")
    print("=" * 95)
    print(f"  • Computed SHA-256 Signature: {sig}")
    print(f"  • Signature Verification: {'✅ VERIFIED (100% Authentic)' if valid else '❌ FAILED'}")
    print("=" * 95)
    print("🎉 Remediation 3: Data Provenance Signing & Poisoning Defense Active!")


if __name__ == "__main__":
    main()
