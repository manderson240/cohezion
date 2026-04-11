"""Constitutional enforcer — deterministic runtime constraint checker.

Blocks tool calls matching CONSTITUTION.md hard constraint violations.
Uses regex/keyword matching only — no LLM reasoning in the enforcement path.

References:
    - .agent/CONSTITUTION.md Section 6: Hard constraints
    - Session 96b Phase 4.7: Machine-enforceable constraints
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ViolationType(str, Enum):
    DESTRUCTIVE_COMMAND = "destructive_command"
    INFRASTRUCTURE_ATTACK = "infrastructure_attack"
    SECRET_EXPOSURE = "secret_exposure"
    UNAUTHORIZED_NETWORK = "unauthorized_network"


@dataclass(frozen=True)
class Violation:
    violation_type: ViolationType
    pattern_matched: str
    input_text: str
    description: str


class ConstitutionalEnforcer:
    """Deterministic checker for CONSTITUTION.md hard constraints.

    All checks are regex/keyword — no LLM reasoning.

    Hard constraints enforced (Section 6):
    - No destructive system commands (rm -rf /, mkfs, fork bomb, raw disk writes)
    - No critical infrastructure attacks (network scanners, brute-force tools)
    - No secret/credential exposure via print/echo
    """

    # Destructive commands that should never execute.
    # rm -rf / is caught but rm -rf /tmp/foo is intentionally allowed.
    DESTRUCTIVE_PATTERNS = [
        r"rm\s+-rf\s+/(?!\w)",  # rm -rf / (not rm -rf /tmp/foo)
        r"mkfs\b",  # Format filesystem
        r"dd\s+if=.*\s+of=/dev/",  # Raw disk writes
        r":\(\)\s*\{\s*:\|:\s*&\s*\}",  # Fork bomb
        r"chmod\s+-R\s+777\s+/",  # World-writable root
    ]

    # Infrastructure attack patterns (Section 6: Critical Infrastructure).
    INFRA_ATTACK_PATTERNS = [
        r"nmap\b",
        r"masscan\b",
        r"sqlmap\b",
        r"hydra\b.*-l\b",  # Brute force with login flag
    ]

    # Secret exposure patterns — print/echo of credentials.
    SECRET_PATTERNS = [
        r"(?i)(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}",
        r"(?i)print\(.*(?:password|secret|api_key)",
        r"(?i)echo\s+\$\{?(?:PASSWORD|SECRET|API_KEY)",
    ]

    def __init__(
        self,
        extra_patterns: list[tuple[ViolationType, str]] | None = None,
    ) -> None:
        self._compiled: list[tuple[ViolationType, re.Pattern[str], str]] = []

        for pat in self.DESTRUCTIVE_PATTERNS:
            self._compiled.append((ViolationType.DESTRUCTIVE_COMMAND, re.compile(pat), pat))
        for pat in self.INFRA_ATTACK_PATTERNS:
            self._compiled.append((ViolationType.INFRASTRUCTURE_ATTACK, re.compile(pat), pat))
        for pat in self.SECRET_PATTERNS:
            self._compiled.append((ViolationType.SECRET_EXPOSURE, re.compile(pat), pat))
        if extra_patterns:
            for vtype, pat in extra_patterns:
                self._compiled.append((vtype, re.compile(pat), pat))

    def check(self, input_text: str) -> list[Violation]:
        """Check input text against all constitutional constraints.

        Returns list of violations (empty = safe).
        """
        violations: list[Violation] = []
        for vtype, compiled, raw_pat in self._compiled:
            if compiled.search(input_text):
                violations.append(
                    Violation(
                        violation_type=vtype,
                        pattern_matched=raw_pat,
                        input_text=input_text[:200],
                        description=f"{vtype.value}: matched pattern '{raw_pat}'",
                    )
                )
                logger.warning(
                    "Constitutional violation detected: type=%s pattern='%s'",
                    vtype.value,
                    raw_pat,
                )
        return violations

    def is_safe(self, input_text: str) -> bool:
        """Quick check: returns True if no violations found."""
        return len(self.check(input_text)) == 0

    def enforce(self, input_text: str) -> None:
        """Raise ValueError if any violations found.

        Raises:
            ValueError: When one or more constitutional violations are detected.
        """
        violations = self.check(input_text)
        if violations:
            descs = [v.description for v in violations]
            raise ValueError(f"Constitutional violation(s): {'; '.join(descs)}")


class ConstitutionalGuardrail:
    """Adapts ConstitutionalEnforcer to GuardrailPipeline's Guardrail protocol.

    Usage:
        from cohezion.security.guardrail_pipeline import GuardrailPipeline
        pipeline = GuardrailPipeline(guardrails=[
            ("constitutional", ConstitutionalGuardrail()),
            ...
        ])
    """

    def __init__(self, enforcer: ConstitutionalEnforcer | None = None):
        self._enforcer = enforcer or ConstitutionalEnforcer()

    async def check(self, text: str, context: dict | None = None) -> "GuardrailResult":
        """Check text against constitutional constraints.

        Returns BLOCK with violation details, or ALLOW if safe.
        """
        from cohezion.security.guardrail_pipeline import GuardrailAction, GuardrailResult

        violations = self._enforcer.check(text)
        if violations:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason="; ".join(v.description for v in violations),
                guard_name="constitutional",
                metadata={"violation_count": len(violations)},
            )
        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            guard_name="constitutional",
        )
