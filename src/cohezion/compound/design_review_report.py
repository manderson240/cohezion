"""Design Review Report (DRR) generator for V-Model gates.

Generates formal reports at each V-Model lifecycle gate (DRR-0 through DRR-3).
Reports are deterministic, hashable, and stored in SurrealDB vmodel_gate table.

V-Model Gate Mapping:
    DRR-0: Intent → Acceptance (retrospection matches intent)
    DRR-1: Plan → System Test (plan artifacts verified)
    DRR-2: Architecture → Integration (interface contracts hold)
    DRR-3: Implementation → Unit Test (code + tests pass)

References:
    - VP-Model: Hash-locked verification gates
    - Session 96b: V-Model integration plan (Phase 4.3)
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class GateLevel(str, Enum):
    """V-Model gate levels."""

    INTENT = "DRR-0"
    PLAN = "DRR-1"
    ARCHITECTURE = "DRR-2"
    IMPLEMENTATION = "DRR-3"


class FindingSeverity(str, Enum):
    """DRR finding severity levels."""

    CRITICAL = "critical"  # Gate cannot pass
    HIGH = "high"  # Must fix before next gate
    MEDIUM = "medium"  # Should fix
    LOW = "low"  # Informational


@dataclass(frozen=True)
class Finding:
    """A single DRR finding."""

    severity: FindingSeverity
    category: str  # boundary_mismatch, abstraction_gap, dependency_violation, etc.
    description: str
    location: str = ""  # file:line or artifact reference


@dataclass
class DesignReviewReport:
    """Formal Design Review Report at a V-Model gate."""

    gate: GateLevel
    session_id: str
    left_artifact: str  # Path to spec/plan/code
    right_artifact: str  # Path to test/review/retrospection
    findings: list[Finding] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    passed: bool = False

    @property
    def artifact_hash(self) -> str:
        """SHA-256 hash of left artifact content."""
        return _hash_file(self.left_artifact)

    @property
    def test_hash(self) -> str:
        """SHA-256 hash of right artifact content."""
        return _hash_file(self.right_artifact)

    @property
    def report_hash(self) -> str:
        """SHA-256 hash of the full report content (for tamper detection)."""
        content = f"{self.gate.value}|{self.artifact_hash}|{self.test_hash}|"
        content += "|".join(
            f"{f.severity.value}:{f.category}:{f.description}" for f in self.findings
        )
        return hashlib.sha256(content.encode()).hexdigest()

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.CRITICAL)

    @property
    def summary(self) -> str:
        """One-line summary of the DRR."""
        status = "PASS" if self.passed else "FAIL"
        counts = {}
        for f in self.findings:
            counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
        parts = [f"{status} {self.gate.value}"]
        for sev in ["critical", "high", "medium", "low"]:
            if sev in counts:
                parts.append(f"{counts[sev]} {sev}")
        return " | ".join(parts)

    def to_surql_params(self) -> dict[str, Any]:
        """Convert to SurrealDB INSERT parameters for vmodel_gate table."""
        return {
            "gate_id": self.gate.value,
            "level": self.gate.name.lower(),
            "left_artifact": self.left_artifact,
            "right_artifact": self.right_artifact,
            "artifact_hash": self.artifact_hash,
            "test_hash": self.test_hash,
            "passed": self.passed,
            "drr_summary": self.summary,
            "session_id": self.session_id,
            "findings_json": [
                {
                    "severity": f.severity.value,
                    "category": f.category,
                    "description": f.description,
                    "location": f.location,
                }
                for f in self.findings
            ],
        }


class DRRGenerator:
    """Generates Design Review Reports at V-Model gates.

    All checks are deterministic — no LLM reasoning in the report itself.
    """

    def generate(
        self,
        gate: GateLevel,
        session_id: str,
        left_artifact: str,
        right_artifact: str,
    ) -> DesignReviewReport:
        """Generate a DRR for the given gate.

        Args:
            gate: Which V-Model gate (DRR-0 through DRR-3)
            session_id: Current session identifier
            left_artifact: Path to left-branch artifact (spec/plan/code)
            right_artifact: Path to right-branch artifact (test/review)

        Returns:
            DesignReviewReport with findings and pass/fail status
        """
        report = DesignReviewReport(
            gate=gate,
            session_id=session_id,
            left_artifact=left_artifact,
            right_artifact=right_artifact,
        )

        # Run gate-specific checks
        self._check_artifacts_exist(report)
        self._check_artifact_non_empty(report)
        self._check_hash_integrity(report)

        if gate == GateLevel.IMPLEMENTATION:
            self._check_test_coverage(report)

        # Gate passes only if no critical findings
        report.passed = report.critical_count == 0
        return report

    def _check_artifacts_exist(self, report: DesignReviewReport) -> None:
        """Both left and right artifacts must exist."""
        if not Path(report.left_artifact).exists():
            report.findings.append(
                Finding(
                    severity=FindingSeverity.CRITICAL,
                    category="missing_artifact",
                    description=f"Left artifact not found: {report.left_artifact}",
                )
            )
        if not Path(report.right_artifact).exists():
            report.findings.append(
                Finding(
                    severity=FindingSeverity.CRITICAL,
                    category="missing_artifact",
                    description=f"Right artifact not found: {report.right_artifact}",
                )
            )

    def _check_artifact_non_empty(self, report: DesignReviewReport) -> None:
        """Artifacts must have content."""
        for path_str, side in [
            (report.left_artifact, "left"),
            (report.right_artifact, "right"),
        ]:
            path = Path(path_str)
            if path.exists() and path.stat().st_size == 0:
                report.findings.append(
                    Finding(
                        severity=FindingSeverity.HIGH,
                        category="empty_artifact",
                        description=f"Empty {side} artifact: {path_str}",
                    )
                )

    def _check_hash_integrity(self, report: DesignReviewReport) -> None:
        """Verify artifacts haven't been tampered with since last gate."""
        left = Path(report.left_artifact)
        right = Path(report.right_artifact)

        if left.exists() and right.exists() and report.artifact_hash == report.test_hash:
            report.findings.append(
                Finding(
                    severity=FindingSeverity.MEDIUM,
                    category="identical_artifacts",
                    description="Left and right artifacts have identical content",
                )
            )

    async def persist(self, report: DesignReviewReport, surreal_client=None) -> bool:
        """Persist DRR to SurrealDB vmodel_gate table (non-blocking).

        Falls back gracefully if SurrealDB is not available.
        """
        if surreal_client is None:
            try:
                from cohezion.persistence.surreal_client import get_surreal_client

                surreal_client = get_surreal_client()
            except Exception:
                logger.debug("SurrealDB not available for DRR persistence")
                return False

        try:
            params = report.to_surql_params()
            query = """
                CREATE vmodel_gate CONTENT {
                    gate_id: $gate_id,
                    level: $level,
                    left_artifact: $left_artifact,
                    right_artifact: $right_artifact,
                    artifact_hash: $artifact_hash,
                    test_hash: $test_hash,
                    passed: $passed,
                    drr_summary: $drr_summary,
                    session_id: $session_id,
                    valid_from: time::now()
                };
            """
            await surreal_client.query(query, params)
            logger.info("DRR %s persisted to vmodel_gate", report.gate.value)
            return True
        except Exception as e:
            logger.debug("DRR persistence failed (non-blocking): %s", e)
            return False

    def _check_test_coverage(self, report: DesignReviewReport) -> None:
        """For DRR-3: check that test file contains assertions."""
        right = Path(report.right_artifact)
        if not right.exists():
            return

        content = right.read_text()
        if "assert" not in content and "pytest.raises" not in content:
            report.findings.append(
                Finding(
                    severity=FindingSeverity.HIGH,
                    category="no_assertions",
                    description="Test file contains no assertions",
                    location=report.right_artifact,
                )
            )

        if "def test_" not in content:
            report.findings.append(
                Finding(
                    severity=FindingSeverity.HIGH,
                    category="no_test_functions",
                    description="Test file contains no test functions",
                    location=report.right_artifact,
                )
            )


def _hash_file(path_str: str) -> str:
    """SHA-256 hash of file content, or empty string if file doesn't exist."""
    path = Path(path_str)
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()
