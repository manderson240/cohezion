# ruff: noqa: RUF012  # class attrs treated as immutable config; never mutated per-instance
"""Constitutional Shielding & Auto-Incinerator (Story 4.3, NFR-10).

Audits code and agent outputs against Anthropic's safety criteria
(the Constitution). Unsafe patterns are permanently blacklisted.
Ambiguous results are quarantined for Triune Consensus review.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)

# Safety score thresholds
SAFE_THRESHOLD = 0.7
UNSAFE_THRESHOLD = 0.3


class AuditVerdict(Enum):
    SAFE = "safe"
    QUARANTINED = "quarantined"
    INCINERATED = "incinerated"


@dataclass
class AuditRecord:
    """Result of a Constitutional audit."""

    content_hash: str
    verdict: AuditVerdict
    safety_score: float
    reasons: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "content_hash": self.content_hash,
            "verdict": self.verdict.value,
            "safety_score": self.safety_score,
            "reasons": self.reasons,
            "timestamp": self.timestamp,
        }


class ConstitutionalShield:
    """Audits content against the Constitution and enforces safety.

    Three outcomes:
    - SAFE (score >= 0.7): Content passes, no action needed
    - QUARANTINED (0.3 <= score < 0.7): Ambiguous, escalated to Triune
    - INCINERATED (score < 0.3): Unsafe, permanently blacklisted
    """

    # Patterns that are always unsafe (simplified for demonstration)
    UNSAFE_PATTERNS = [
        "rm -rf /",
        "DROP TABLE",
        "DELETE FROM",
        "__import__('os').system",
    ]

    def __init__(
        self,
        safe_threshold: float = SAFE_THRESHOLD,
        unsafe_threshold: float = UNSAFE_THRESHOLD,
    ) -> None:
        self._safe_threshold = safe_threshold
        self._unsafe_threshold = unsafe_threshold
        self._blacklist: set[str] = set()
        self._quarantine: list[AuditRecord] = []
        self._audit_log: list[AuditRecord] = []

    @property
    def blacklist(self) -> set[str]:
        return set(self._blacklist)

    @property
    def quarantine(self) -> list[AuditRecord]:
        return list(self._quarantine)

    def audit(self, content: str) -> AuditRecord:
        """Audit content against the Constitution."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Already blacklisted?
        if content_hash in self._blacklist:
            record = AuditRecord(
                content_hash=content_hash,
                verdict=AuditVerdict.INCINERATED,
                safety_score=0.0,
                reasons=["Previously blacklisted"],
            )
            self._audit_log.append(record)
            return record

        safety_score, reasons = self._compute_safety_score(content)

        if safety_score < self._unsafe_threshold:
            verdict = AuditVerdict.INCINERATED
            self._blacklist.add(content_hash)
            logger.warning("Content INCINERATED: %s", content_hash[:16])
        elif safety_score < self._safe_threshold:
            verdict = AuditVerdict.QUARANTINED
            logger.info("Content QUARANTINED for Triune review: %s", content_hash[:16])
        else:
            verdict = AuditVerdict.SAFE

        record = AuditRecord(
            content_hash=content_hash,
            verdict=verdict,
            safety_score=safety_score,
            reasons=reasons,
        )

        if verdict == AuditVerdict.QUARANTINED:
            self._quarantine.append(record)

        self._audit_log.append(record)
        return record

    def _compute_safety_score(self, content: str) -> tuple[float, list[str]]:
        """Compute safety score based on pattern matching."""
        reasons: list[str] = []
        score = 1.0
        content_lower = content.lower()

        for pattern in self.UNSAFE_PATTERNS:
            if pattern.lower() in content_lower:
                score -= 0.4
                reasons.append(f"Unsafe pattern detected: {pattern}")

        if not content.strip():
            score -= 0.1
            reasons.append("Empty content")

        return max(0.0, score), reasons

    def is_blacklisted(self, content: str) -> bool:
        """Check if content hash is permanently blacklisted."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return content_hash in self._blacklist

    def get_audit_log(self) -> list[dict]:
        """Export audit log for observability."""
        return [r.to_dict() for r in self._audit_log]
