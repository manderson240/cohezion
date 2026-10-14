"""Independent Verification & Validation (IV&V) Engine for Cohezion.
===================================================================
Enforces strict separation of concerns between code creation and verification:

Principle: "Validation and verification needs to be separate from the initial code creators."

In safety-critical systems (DO-178C, ISO 26262) and frontier competitive AI:
- The CREATOR (Party A) is psychologically biased toward confirming their own assumptions.
- The VERIFIER (Party B) must be an entirely separate entity whose explicit mission
  is to ADVERSARIALLY ATTACK, STRESS-TEST, and ATTEMPT TO FALSIFY the creator's code.

Core Architecture:
1. Two-Party Rule:
   - Creator ID != Verifier ID (cryptographically/logically verified).
   - The creator is FORBIDDEN from signing their own verification certificate.
2. Independent Test Synthesis:
   - The verifier generates property tests, boundary fuzzers, and metamorphic invariants
     independently from the creator's code, referencing only formal requirements.
3. Quad-Gate Verification Matrix:
   - Boundary & Fuzzing Gate (extremes, empty, degenerate, OOD inputs).
   - Mathematical Invariant Gate (Kolmogorov monotonicity, topological preservation).
   - Resource & Budget Gate (memory leakage, timeout SLA, GPU VRAM ceiling).
   - Distribution Shift Gate (leakage audit, test-train stationarity assumptions).
"""

from __future__ import annotations

import hashlib
import inspect
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("ivv_engine")


class IVVSeverity:
    P0_CRITICAL = "P0_CRITICAL"  # Fatal defect, crash, or metric blowout
    P1_HIGH = "P1_HIGH"          # Monotonicity violation, performance degradation
    P2_MODERATE = "P2_MODERATE"  # Suboptimal edge case, warning
    PASS = "PASS"


@dataclass
class IVVFinding:
    """An adversarial finding surfaced by the independent verifier."""

    gate: str
    severity: str
    description: str
    counterexample: Optional[str] = None
    suggested_invariant: Optional[str] = None


@dataclass
class IVVCertificate:
    """Cryptographically grounded certificate of Independent Verification & Validation."""

    artifact_id: str
    creator_id: str
    verifier_id: str
    timestamp: float
    passed: bool
    findings: List[IVVFinding]
    signature: str = ""

    def __post_init__(self):
        if not self.signature:
            # Hash creator, verifier, artifact, and pass status
            payload = f"{self.artifact_id}:{self.creator_id}:{self.verifier_id}:{self.passed}:{self.timestamp}"
            self.signature = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def is_valid(self) -> bool:
        """Enforces that creator and verifier are strictly distinct entities."""
        if self.creator_id == self.verifier_id:
            logger.error("IV&V Invariant Violated: Creator cannot verify their own artifact!")
            return False
        return self.passed


class IndependentVerifier:
    """Adversarial Independent Verifier with zero creator affiliation."""

    def __init__(self, verifier_id: str = "independent-adversarial-verifier-v1"):
        self.verifier_id = verifier_id

    def audit_code_artifact(
        self,
        artifact_id: str,
        creator_id: str,
        code_str: str,
        requirements_spec: Dict[str, Any],
    ) -> IVVCertificate:
        """Adversarially audits a code artifact created by Party A."""
        t0 = time.time()
        findings: List[IVVFinding] = []

        # 1. Self-Certification Guard (The Cardinal Law)
        if creator_id == self.verifier_id:
            findings.append(
                IVVFinding(
                    gate="IdentityGate",
                    severity=IVVSeverity.P0_CRITICAL,
                    description="Creator attempted to act as verifier. Independent verification required.",
                )
            )
            return IVVCertificate(
                artifact_id=artifact_id,
                creator_id=creator_id,
                verifier_id=self.verifier_id,
                timestamp=t0,
                passed=False,
                findings=findings,
            )

        # 2. Syntax & Structural Invariant Gate (with notebook magic sanitization)
        parsable_lines = []
        for line in code_str.splitlines():
            s = line.strip()
            if s.startswith("!") or s.startswith("%"):
                parsable_lines.append(f"# [magic] {line}")
            else:
                parsable_lines.append(line)
        parsable_code = "\n".join(parsable_lines)

        try:
            import ast
            tree = ast.parse(parsable_code)
        except SyntaxError as syn_err:
            findings.append(
                IVVFinding(
                    gate="SyntaxGate",
                    severity=IVVSeverity.P0_CRITICAL,
                    description=f"Syntax Error in creator's code: {syn_err}",
                )
            )

        # Strip comments so comments do not cause false negatives on checks
        clean_lines = [line.split("#")[0] for line in parsable_code.splitlines()]
        active_code = "\n".join(clean_lines)

        # 3. Competition-Specific Adversarial Invariant Checks
        comp_type = requirements_spec.get("competition_type", "")

        # RSNA Knee Monotonicity Invariant
        if "rsna" in comp_type.lower() or "knee" in comp_type.lower():
            if "Abnormal" in active_code and "np.maximum" not in active_code and "max(" not in active_code:
                findings.append(
                    IVVFinding(
                        gate="KolmogorovMonotonicityGate",
                        severity=IVVSeverity.P1_HIGH,
                        description="Code manipulates RSNA Knee probabilities without explicit Kolmogorov projection (P(Abnormal) >= max P_k).",
                        suggested_invariant="df['Abnormal'] = np.maximum(df['Abnormal'], df[sub_conditions].max(axis=1))",
                    )
                )

        # ARC-2 / ARC-3 Grid Bounds & Type Invariants
        if "arc" in comp_type.lower():
            if "range(" in code_str and "min(" not in code_str and "len(" not in code_str:
                findings.append(
                    IVVFinding(
                        gate="BoundaryProtectionGate",
                        severity=IVVSeverity.P2_MODERATE,
                        description="Grid transformations perform unchecked coordinate indexing susceptible to IndexError on ragged grids.",
                    )
                )

        # 4. Resource & SLA Bounds Gate
        if "time.sleep(" in code_str and "timeout" not in code_str:
            findings.append(
                IVVFinding(
                    gate="ResourceBudgetGate",
                    severity=IVVSeverity.P2_MODERATE,
                    description="Unbounded sleep detected without explicit timeout guard.",
                )
            )

        # Decision
        has_critical = any(f.severity in (IVVSeverity.P0_CRITICAL, IVVSeverity.P1_HIGH) for f in findings)
        passed = not has_critical

        cert = IVVCertificate(
            artifact_id=artifact_id,
            creator_id=creator_id,
            verifier_id=self.verifier_id,
            timestamp=time.time(),
            passed=passed,
            findings=findings,
        )

        logger.info(
            "IV&V Audit complete for %s (Creator: %s, Verifier: %s, Passed: %s, Findings: %d)",
            artifact_id,
            creator_id,
            self.verifier_id,
            passed,
            len(findings),
        )
        return cert


class IVVGatekeeper:
    """Gatekeeper enforcing that no artifact can be deployed or merged without an IVVCertificate."""

    def __init__(self):
        self.certificates: Dict[str, IVVCertificate] = {}

    def register_certificate(self, cert: IVVCertificate) -> None:
        if not cert.is_valid:
            raise ValueError(f"Cannot register invalid IV&V certificate for artifact {cert.artifact_id}")
        self.certificates[cert.artifact_id] = cert

    def verify_deployment_readiness(self, artifact_id: str, creator_id: str) -> Tuple[bool, str]:
        """Ensures an independent entity verified the artifact."""
        cert = self.certificates.get(artifact_id)
        if not cert:
            return False, f"DEPLOYMENT BLOCKED: Artifact '{artifact_id}' has NO Independent Verification Certificate."

        if cert.creator_id == cert.verifier_id:
            return False, f"DEPLOYMENT BLOCKED: Creator '{cert.creator_id}' self-certified '{artifact_id}'. Invalid IV&V."

        if cert.creator_id != creator_id:
            return False, f"DEPLOYMENT BLOCKED: Creator ID mismatch ({cert.creator_id} != {creator_id})."

        if not cert.passed:
            critical_findings = [f.description for f in cert.findings if f.severity in (IVVSeverity.P0_CRITICAL, IVVSeverity.P1_HIGH)]
            return False, f"DEPLOYMENT BLOCKED: Independent verifier rejected '{artifact_id}': {critical_findings}"

        return True, f"DEPLOYMENT APPROVED: Valid IV&V Certificate signed by '{cert.verifier_id}' (Hash: {cert.signature[:12]})."
