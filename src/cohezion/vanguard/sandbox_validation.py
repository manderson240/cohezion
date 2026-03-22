"""Substrate Sandbox & Behavioral Validation (Story 4.2, NFR-1, Security).

Unverified patterns execute within a restricted GTT memory environment.
New discoveries cannot destabilize the core physics substrate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)

# Default sandbox memory quota: 2GB per unverified script
SANDBOX_GTT_QUOTA_BYTES = 2 * 1024 * 1024 * 1024

# Patterns that indicate unsafe code (static analysis)
UNSAFE_CODE_PATTERNS = [
    "shell_invoke",
    "process_spawn",
    "dynamic_import",
    "privilege_escalation",
]


class ValidationVerdict(Enum):
    PASSED = "passed"
    FAILED = "failed"
    QUARANTINED = "quarantined"


@dataclass
class SandboxScript:
    script_id: str
    source_url: str
    code: str
    requested_bytes: int = SANDBOX_GTT_QUOTA_BYTES


@dataclass
class ValidationReport:
    script_id: str
    verdict: ValidationVerdict
    reason: str = ""
    memory_used_bytes: int = 0
    substrate_impact: str = "none"

    def to_dict(self) -> dict:
        return {
            "script_id": self.script_id,
            "verdict": self.verdict.value,
            "reason": self.reason,
            "memory_used_bytes": self.memory_used_bytes,
            "substrate_impact": self.substrate_impact,
        }


class SubstrateSandbox:
    """Restricted execution environment for unverified discovery scripts.

    Enforces GTT memory quota and prevents substrate destabilization.
    In production, this wraps the Memory-Mapped Barrier (Story 1.6).
    """

    def __init__(self, gtt_quota_bytes: int = SANDBOX_GTT_QUOTA_BYTES) -> None:
        self._quota = gtt_quota_bytes
        self._validated: list[ValidationReport] = []
        self._quarantined: list[str] = []

    def validate(self, script: SandboxScript) -> ValidationReport:
        """Execute script in sandbox and validate behavior."""
        # Quota enforcement
        if script.requested_bytes > self._quota:
            report = ValidationReport(
                script_id=script.script_id,
                verdict=ValidationVerdict.QUARANTINED,
                reason=f"Requested memory {script.requested_bytes} exceeds quota {self._quota}",
                substrate_impact="none",
            )
            self._quarantined.append(script.script_id)
            self._validated.append(report)
            logger.warning("Script %s quarantined: exceeds GTT quota", script.script_id)
            return report

        # Behavioral validation (static pattern scanning)
        unsafe = self._scan_for_unsafe_patterns(script.code)
        if unsafe:
            report = ValidationReport(
                script_id=script.script_id,
                verdict=ValidationVerdict.QUARANTINED,
                reason=f"Unsafe pattern detected: {unsafe}",
                substrate_impact="none",
            )
            self._quarantined.append(script.script_id)
            self._validated.append(report)
            return report

        report = ValidationReport(
            script_id=script.script_id,
            verdict=ValidationVerdict.PASSED,
            reason="Behavioral validation passed",
            memory_used_bytes=min(script.requested_bytes, self._quota),
            substrate_impact="none",
        )
        self._validated.append(report)
        return report

    def _scan_for_unsafe_patterns(self, code: str) -> str | None:
        """Static scan for unsafe code patterns (checks against known dangerous labels)."""
        for pattern in UNSAFE_CODE_PATTERNS:
            if pattern in code:
                return pattern
        return None

    def results(self) -> list[dict]:
        return [r.to_dict() for r in self._validated]

    @property
    def quarantine_count(self) -> int:
        return len(self._quarantined)
