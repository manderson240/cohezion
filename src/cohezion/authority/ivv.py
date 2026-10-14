"""Two-Party Cryptographic IV&V Authority & Dual Attestation for Cohezion.

Permanently eliminates creator self-certification regressions by requiring
cryptographically verified DualAttestation before any artifact, model,
skill, or Kaggle submission is promoted to production.

Key Guarantees:
1. Strict Dual Attestation: Creator cannot be verifier (`creator_id != verifier_id`).
2. Cryptographic Attestation: HMAC-SHA256 signatures generated using authority key
   (~/.cohezion/security/ivv_authority.key, chmod 0600).
3. TransparencyLog: Tamper-evident SHA-256 hash-chain of all certified promotions.
4. Independent Evidence: Verifier must supply digest of verifier-owned test suite.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cohezion.compound.ivv_authority import (
    IVVAssertion,
    IVVAuthority,
    IVVFinding,
    IVVKeyManager,
    IVVSeverity,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreatorAttestation:
    """Attestation emitted by the code/model/skill creator."""

    artifact_digest: str
    creator_id: str
    claim: str
    nonce: str
    policy_id: str
    timestamp: float
    signature: str

    def payload_bytes(self) -> bytes:
        payload = f"{self.artifact_digest}:{self.creator_id}:{self.claim}:{self.nonce}:{self.policy_id}:{self.timestamp}"
        return payload.encode("utf-8")


@dataclass(frozen=True)
class VerifierAttestation:
    """Attestation emitted by an independent verification agent."""

    artifact_digest: str
    verifier_id: str
    verdict: bool
    evidence_digest: str
    nonce: str
    policy_id: str
    timestamp: float
    signature: str

    def payload_bytes(self) -> bytes:
        payload = f"{self.artifact_digest}:{self.verifier_id}:{self.verdict}:{self.evidence_digest}:{self.nonce}:{self.policy_id}:{self.timestamp}"
        return payload.encode("utf-8")


@dataclass(frozen=True)
class DualAttestation:
    """Cryptographic proof of dual-party verification required for promotion."""

    artifact_digest: str
    creator: CreatorAttestation
    verifier: VerifierAttestation
    promoted_at: float
    policy_id: str
    merkle_leaf_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_digest": self.artifact_digest,
            "creator": asdict(self.creator),
            "verifier": asdict(self.verifier),
            "promoted_at": self.promoted_at,
            "policy_id": self.policy_id,
            "merkle_leaf_hash": self.merkle_leaf_hash,
        }


@dataclass
class TransparencyLogEntry:
    """An entry in the tamper-evident transparency hash chain."""

    index: int
    prev_hash: str
    artifact_digest: str
    dual_attestation_hash: str
    timestamp: float
    entry_hash: str


class TransparencyLog:
    """Append-only cryptographic hash chain recording all verified promotions."""

    def __init__(self, log_path: Optional[Path] = None) -> None:
        if log_path is None:
            log_path = Path.home() / ".cohezion" / "security" / "transparency_log.jsonl"
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: List[TransparencyLogEntry] = []
        self._load()

    def _load(self) -> None:
        self._entries.clear()
        if not self.log_path.exists():
            return
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                self._entries.append(
                    TransparencyLogEntry(
                        index=d["index"],
                        prev_hash=d["prev_hash"],
                        artifact_digest=d["artifact_digest"],
                        dual_attestation_hash=d["dual_attestation_hash"],
                        timestamp=d["timestamp"],
                        entry_hash=d["entry_hash"],
                    )
                )

    @property
    def latest_hash(self) -> str:
        if not self._entries:
            return "0" * 64
        return self._entries[-1].entry_hash

    def append(self, dual_attestation: DualAttestation) -> TransparencyLogEntry:
        prev_hash = self.latest_hash
        index = len(self._entries)
        attestation_bytes = json.dumps(dual_attestation.to_dict(), sort_keys=True).encode()
        da_hash = hashlib.sha256(attestation_bytes).hexdigest()
        now = time.time()

        content = f"{index}:{prev_hash}:{dual_attestation.artifact_digest}:{da_hash}:{now}"
        entry_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        entry = TransparencyLogEntry(
            index=index,
            prev_hash=prev_hash,
            artifact_digest=dual_attestation.artifact_digest,
            dual_attestation_hash=da_hash,
            timestamp=now,
            entry_hash=entry_hash,
        )

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "index": entry.index,
                        "prev_hash": entry.prev_hash,
                        "artifact_digest": entry.artifact_digest,
                        "dual_attestation_hash": entry.dual_attestation_hash,
                        "timestamp": entry.timestamp,
                        "entry_hash": entry.entry_hash,
                    }
                )
                + "\n"
            )
        self._entries.append(entry)
        return entry

    def verify_integrity(self) -> bool:
        """Verifies the entire hash chain from genesis to head."""
        prev = "0" * 64
        for idx, entry in enumerate(self._entries):
            if entry.index != idx:
                return False
            if entry.prev_hash != prev:
                return False
            content = f"{entry.index}:{entry.prev_hash}:{entry.artifact_digest}:{entry.dual_attestation_hash}:{entry.timestamp}"
            expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if entry.entry_hash != expected:
                return False
            prev = entry.entry_hash
        return True


class IVVPolicy:
    """Policy rules governing valid DualAttestation."""

    def __init__(self, key_manager: Optional[IVVKeyManager] = None) -> None:
        self.km = key_manager or IVVKeyManager()

    def create_creator_attestation(
        self,
        artifact_path: Path,
        creator_id: str,
        claim: str,
        policy_id: str = "cohezion-standard-v1",
    ) -> CreatorAttestation:
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")
        digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        nonce = os.urandom(16).hex()
        ts = time.time()
        payload = f"{digest}:{creator_id}:{claim}:{nonce}:{policy_id}:{ts}".encode("utf-8")
        sig = self.km.sign(payload)
        return CreatorAttestation(
            artifact_digest=digest,
            creator_id=creator_id,
            claim=claim,
            nonce=nonce,
            policy_id=policy_id,
            timestamp=ts,
            signature=sig,
        )

    def create_verifier_attestation(
        self,
        artifact_path: Path,
        verifier_id: str,
        verdict: bool,
        evidence_path: Path,
        nonce: str,
        policy_id: str = "cohezion-standard-v1",
    ) -> VerifierAttestation:
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")
        if not evidence_path.exists():
            raise FileNotFoundError(f"Evidence not found: {evidence_path}")

        artifact_digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        evidence_digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        ts = time.time()
        payload = f"{artifact_digest}:{verifier_id}:{verdict}:{evidence_digest}:{nonce}:{policy_id}:{ts}".encode("utf-8")
        sig = self.km.sign(payload)
        return VerifierAttestation(
            artifact_digest=artifact_digest,
            verifier_id=verifier_id,
            verdict=verdict,
            evidence_digest=evidence_digest,
            nonce=nonce,
            policy_id=policy_id,
            timestamp=ts,
            signature=sig,
        )

    def assemble_dual_attestation(
        self,
        creator: CreatorAttestation,
        verifier: VerifierAttestation,
    ) -> DualAttestation:
        # Enforce Two-Party Rule
        if creator.creator_id == verifier.verifier_id:
            raise ValueError(
                f"Independence Violation: Creator '{creator.creator_id}' cannot self-verify."
            )

        if creator.artifact_digest != verifier.artifact_digest:
            raise ValueError(
                f"Digest Mismatch: Creator digest {creator.artifact_digest} != Verifier digest {verifier.artifact_digest}"
            )

        if not verifier.verdict:
            raise ValueError("Verification Failed: Verifier rejected the artifact.")

        if creator.policy_id != verifier.policy_id:
            raise ValueError(
                f"Policy Mismatch: Creator policy {creator.policy_id} != Verifier policy {verifier.policy_id}"
            )

        # Cryptographic verification of both signatures
        if not self.km.verify(creator.payload_bytes(), creator.signature):
            raise ValueError("Cryptographic Failure: Creator signature invalid or forged.")

        if not self.km.verify(verifier.payload_bytes(), verifier.signature):
            raise ValueError("Cryptographic Failure: Verifier signature invalid or forged.")

        now = time.time()
        combined = f"{creator.signature}:{verifier.signature}:{now}".encode("utf-8")
        leaf_hash = hashlib.sha256(combined).hexdigest()

        return DualAttestation(
            artifact_digest=creator.artifact_digest,
            creator=creator,
            verifier=verifier,
            promoted_at=now,
            policy_id=creator.policy_id,
            merkle_leaf_hash=leaf_hash,
        )


class PromotionGatekeeper:
    """Enforces DualAttestation at the boundary of all registry promotions."""

    def __init__(
        self,
        policy: Optional[IVVPolicy] = None,
        transparency_log: Optional[TransparencyLog] = None,
    ) -> None:
        self.policy = policy or IVVPolicy()
        self.log = transparency_log or TransparencyLog()

    def certify_and_promote(
        self,
        artifact_path: Path,
        creator_attestation: CreatorAttestation,
        verifier_attestation: VerifierAttestation,
    ) -> DualAttestation:
        """Validates dual attestation, appends to transparency log, and returns certificate."""
        dual_attestation = self.policy.assemble_dual_attestation(
            creator=creator_attestation,
            verifier=verifier_attestation,
        )
        self.log.append(dual_attestation)
        logger.info(
            "DualAttestation verified for %s (Creator: %s, Verifier: %s)",
            artifact_path.name,
            creator_attestation.creator_id,
            verifier_attestation.verifier_id,
        )
        return dual_attestation

    def assert_promotable(
        self,
        artifact_path: Path,
        dual_attestation: DualAttestation,
    ) -> None:
        """Fails closed if the artifact does not match the dual attestation or fails validation."""
        actual_digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if actual_digest != dual_attestation.artifact_digest:
            raise ValueError(
                f"Artifact modified after attestation! Actual {actual_digest} != Certified {dual_attestation.artifact_digest}"
            )
        # Re-verify through policy
        self.policy.assemble_dual_attestation(
            creator=dual_attestation.creator,
            verifier=dual_attestation.verifier,
        )
