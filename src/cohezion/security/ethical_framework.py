"""Ethical Framework (v1.0.2 Phase 6).

Formal ethical decision framework aligned with NIST AI Agent Standards
Initiative (Feb 2026) and OWASP Top 10 for Agentic Applications.

Decision Hierarchy:
    1. Beneficence — does this help the user?
    2. Non-maleficence — could this cause harm?
    3. Autonomy — does the user retain control?
    4. Justice — is this fair and non-discriminatory?

References:
    - NIST AI Agent Standards Initiative (Feb 2026)
    - OWASP Top 10 for Agentic Applications (Dec 2025)
    - Cohezion CONSTITUTION_PRIME.md
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


logger = logging.getLogger(__name__)


class EthicalPrinciple(StrEnum):
    """Four pillars of ethical AI agent behavior."""

    BENEFICENCE = "beneficence"
    NON_MALEFICENCE = "non_maleficence"
    AUTONOMY = "autonomy"
    JUSTICE = "justice"


class RiskLevel(StrEnum):
    """Risk categorization for agent actions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EthicalAssessment:
    """Result of an ethical evaluation."""

    action_description: str
    approved: bool
    risk_level: RiskLevel
    violated_principles: list[EthicalPrinciple] = field(default_factory=list)
    reasoning: str = ""
    requires_consent: bool = False
    mitigations: list[str] = field(default_factory=list)
    audit_id: str = ""


# OWASP Top 10 for Agentic Applications threat patterns
OWASP_AGENTIC_THREATS: dict[str, list[str]] = {
    "tool_misuse": [
        "delete",
        "drop",
        "truncate",
        "rm -rf",
        "format",
        "shutdown",
    ],
    "prompt_injection": [
        "ignore previous",
        "system prompt",
        "jailbreak",
        "DAN",
        "act as",
    ],
    "privilege_escalation": [
        "sudo",
        "admin",
        "root",
        "override",
        "bypass",
    ],
    "data_exfiltration": [
        "send to",
        "upload",
        "email",
        "webhook",
        "curl",
        "fetch",
    ],
    "resource_abuse": [
        "infinite",
        "loop",
        "fork bomb",
        "while true",
    ],
}


class EthicalFramework:
    """Evaluate agent actions against ethical principles.

    Parameters
    ----------
    strict_mode : bool
        If True, any violation blocks the action.
        If False, only CRITICAL violations block.
    """

    def __init__(self, strict_mode: bool = False) -> None:
        self.strict_mode = strict_mode
        self.audit_log: list[EthicalAssessment] = []

    def assess(
        self,
        action: str,
        context: dict[str, Any] | None = None,
    ) -> EthicalAssessment:
        """Assess an agent action for ethical compliance.

        Parameters
        ----------
        action : str
            Description of the action the agent wants to take.
        context : dict, optional
            Additional context (agent_id, target_resource, etc.).

        Returns
        -------
        EthicalAssessment
        """
        context = context or {}
        violations: list[EthicalPrinciple] = []
        risk = RiskLevel.LOW
        mitigations: list[str] = []
        requires_consent = False

        action_lower = action.lower()

        # 1. Non-maleficence check (OWASP threats)
        for threat_type, patterns in OWASP_AGENTIC_THREATS.items():
            for pattern in patterns:
                if pattern in action_lower:
                    violations.append(EthicalPrinciple.NON_MALEFICENCE)
                    risk = RiskLevel.HIGH
                    mitigations.append(f"OWASP {threat_type}: pattern '{pattern}' detected")

        # 2. Autonomy check — irreversible actions need consent
        irreversible_patterns = [
            "delete",
            "destroy",
            "overwrite",
            "deploy",
            "publish",
            "send email",
            "execute payment",
        ]
        for pattern in irreversible_patterns:
            if pattern in action_lower:
                requires_consent = True
                if EthicalPrinciple.AUTONOMY not in violations:
                    violations.append(EthicalPrinciple.AUTONOMY)
                mitigations.append(f"Irreversible action '{pattern}' requires human consent")

        # 3. Justice check — discriminatory patterns
        bias_indicators = [
            "only for",
            "exclude",
            "discriminate",
            "restrict access",
        ]
        for indicator in bias_indicators:
            if indicator in action_lower:
                violations.append(EthicalPrinciple.JUSTICE)
                risk = max(risk, RiskLevel.MEDIUM, key=_risk_order)
                mitigations.append(f"Potential bias indicator: '{indicator}'")

        # 4. Beneficence check — is this actually useful?
        if len(action.strip()) < 5:
            violations.append(EthicalPrinciple.BENEFICENCE)
            mitigations.append("Action too vague to assess benefit")

        # Determine risk level
        if len(violations) >= 3:
            risk = RiskLevel.CRITICAL
        elif len(violations) >= 2:
            risk = max(risk, RiskLevel.HIGH, key=_risk_order)

        # Determine approval
        approved = len(violations) == 0 if self.strict_mode else risk != RiskLevel.CRITICAL

        reasoning_parts = []
        if violations:
            principles = ", ".join(v.value for v in violations)
            reasoning_parts.append(f"Violated principles: {principles}")
        if mitigations:
            reasoning_parts.append(f"Mitigations: {'; '.join(mitigations)}")
        if not violations:
            reasoning_parts.append("No ethical violations detected")

        assessment = EthicalAssessment(
            action_description=action,
            approved=approved,
            risk_level=risk,
            violated_principles=violations,
            reasoning=". ".join(reasoning_parts),
            requires_consent=requires_consent,
            mitigations=mitigations,
            audit_id=f"eth-{int(time.time())}-{len(self.audit_log)}",
        )

        self.audit_log.append(assessment)
        logger.info(
            "Ethical assessment [%s]: %s (risk=%s, violations=%d)",
            assessment.audit_id,
            "APPROVED" if approved else "BLOCKED",
            risk.value,
            len(violations),
        )

        return assessment

    def get_audit_trail(self) -> list[dict[str, Any]]:
        """Return NIST-formatted audit trail."""
        return [
            {
                "audit_id": a.audit_id,
                "action": a.action_description[:100],
                "approved": a.approved,
                "risk_level": a.risk_level.value,
                "violations": [v.value for v in a.violated_principles],
                "requires_consent": a.requires_consent,
                "reasoning": a.reasoning,
            }
            for a in self.audit_log
        ]


def _risk_order(r: RiskLevel) -> int:
    """Order risk levels for comparison."""
    return {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1,
        RiskLevel.HIGH: 2,
        RiskLevel.CRITICAL: 3,
    }[r]
