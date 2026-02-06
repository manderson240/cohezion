"""Unified security pipeline with shared components.

Consolidates PromptGuard and OutputFilter into a single pipeline
to reduce per-agent overhead and improve consistency.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SecurityResult:
    """Result of security check."""

    allowed: bool
    action: str  # "pass", "block", "sanitize"
    reason: str | None = None
    metadata: dict[str, Any] | None = None
    sanitized_content: str | None = None


@dataclass(frozen=True, slots=True)
class FilterResult:
    """Result of output filtering."""

    allowed: bool
    content: str
    violations: list[str]
    risk_score: float  # 0.0 - 1.0


class SecurityRule(Protocol):
    """Protocol for security rules."""

    name: str

    async def check(self, content: str, context: dict[str, Any]) -> SecurityResult: ...


class BaseSecurityRule:
    """Base class for security rules."""

    def __init__(self, name: str, priority: int = 0):
        self.name = name
        self.priority = priority

    async def check(self, content: str, context: dict[str, Any]) -> SecurityResult:
        raise NotImplementedError


class PromptInjectionRule(BaseSecurityRule):
    """Detect prompt injection attempts."""

    # Common injection patterns
    PATTERNS = [
        r"ignore previous instructions",
        r"ignore all prior",
        r"disregard (the )?instructions",
        r"forget (your )?prompt",
        r"system prompt:",
        r"you are now",
        r"new instructions:",
        r"DAN mode",
        r"jailbreak",
        r"bypass (security|filter)",
    ]

    def __init__(self, priority: int = 100):
        super().__init__("prompt_injection", priority)
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]

    async def check(self, content: str, context: dict[str, Any]) -> SecurityResult:
        violations = []
        for pattern in self._compiled:
            if pattern.search(content):
                violations.append(pattern.pattern)

        if violations:
            return SecurityResult(
                allowed=False,
                action="block",
                reason=f"Prompt injection detected: {violations[:3]}",
                metadata={"patterns_matched": violations},
            )

        return SecurityResult(allowed=True, action="pass")


class PIIProtectionRule(BaseSecurityRule):
    """Detect and sanitize PII."""

    # Simple PII patterns (extend with NER for production)
    PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "phone": r"\b\d{3}-\d{3}-\d{4}\b",
        "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    }

    def __init__(self, priority: int = 90, sanitize: bool = True):
        super().__init__("pii_protection", priority)
        self.sanitize = sanitize
        self._compiled = {k: re.compile(v) for k, v in self.PATTERNS.items()}

    async def check(self, content: str, context: dict[str, Any]) -> SecurityResult:
        found_pii = {}
        sanitized = content

        for pii_type, pattern in self._compiled.items():
            matches = pattern.findall(content)
            if matches:
                found_pii[pii_type] = len(matches)
                if self.sanitize:
                    sanitized = pattern.sub(f"[{pii_type}_REDACTED]", sanitized)

        if found_pii:
            return SecurityResult(
                allowed=True,  # Allow but sanitize
                action="sanitize",
                reason=f"PII detected: {found_pii}",
                metadata={"pii_types": list(found_pii.keys())},
                sanitized_content=sanitized if self.sanitize else None,
            )

        return SecurityResult(allowed=True, action="pass")


class ContentModerationRule(BaseSecurityRule):
    """Content moderation for harmful outputs."""

    # Simple keyword-based detection (use ML model for production)
    HARMFUL_PATTERNS = [
        r"\b(kill|murder|assassinate)\s+(yourself|him|her|them)",
        r"\b(how\s+to\s+make|create|build)\s+(bomb|weapon|explosive)",
        r"\b(steal|hack|exploit|bypass)\s+(password|security|system)",
    ]

    def __init__(self, priority: int = 95):
        super().__init__("content_moderation", priority)
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.HARMFUL_PATTERNS]

    async def check(self, content: str, context: dict[str, Any]) -> SecurityResult:
        violations = []
        for pattern in self._compiled:
            if pattern.search(content):
                violations.append(pattern.pattern)

        if violations:
            return SecurityResult(
                allowed=False,
                action="block",
                reason="Harmful content detected",
                metadata={"violations": violations},
            )

        return SecurityResult(allowed=True, action="pass")


class SecurityPipeline:
    """Unified security pipeline for input/output processing.

    Usage:
        pipeline = SecurityPipeline()

        # Check input
        result = await pipeline.check_input(user_prompt)
        if not result.allowed:
            raise SecurityError(result.reason)

        # Check output
        result = await pipeline.check_output(model_response)
        if result.risk_score > 0.8:
            return "[Content filtered]"
    """

    def __init__(self):
        self._input_rules: list[BaseSecurityRule] = []
        self._output_rules: list[BaseSecurityRule] = []
        self._metrics = {
            "inputs_checked": 0,
            "outputs_checked": 0,
            "violations": 0,
            "sanitized": 0,
        }

        # Default rules
        self._add_default_rules()

    def _add_default_rules(self) -> None:
        """Add default security rules."""
        # Input rules
        self.add_input_rule(PromptInjectionRule(priority=100))
        self.add_input_rule(PIIProtectionRule(priority=90, sanitize=True))

        # Output rules
        self.add_output_rule(ContentModerationRule(priority=95))
        self.add_output_rule(PIIProtectionRule(priority=90, sanitize=True))

    def add_input_rule(self, rule: BaseSecurityRule) -> None:
        """Add rule for input validation."""
        self._input_rules.append(rule)
        self._input_rules.sort(key=lambda r: -r.priority)

    def add_output_rule(self, rule: BaseSecurityRule) -> None:
        """Add rule for output filtering."""
        self._output_rules.append(rule)
        self._output_rules.sort(key=lambda r: -r.priority)

    async def check_input(
        self, content: str, context: dict[str, Any] | None = None
    ) -> SecurityResult:
        """Validate input through security rules."""
        self._metrics["inputs_checked"] += 1
        ctx = context or {}

        for rule in self._input_rules:
            result = await rule.check(content, ctx)

            if result.action == "block":
                self._metrics["violations"] += 1
                logger.warning(f"Input blocked by {rule.name}: {result.reason}")
                return result

            if result.action == "sanitize" and result.sanitized_content:
                self._metrics["sanitized"] += 1
                content = result.sanitized_content

        return SecurityResult(allowed=True, action="pass")

    async def check_output(
        self, content: str, context: dict[str, Any] | None = None
    ) -> FilterResult:
        """Filter and validate output content."""
        self._metrics["outputs_checked"] += 1
        ctx = context or {}

        violations = []
        risk_score = 0.0
        filtered_content = content

        for rule in self._output_rules:
            result = await rule.check(filtered_content, ctx)

            if result.action == "block":
                violations.append(f"{rule.name}: {result.reason}")
                risk_score = max(risk_score, 1.0)

            elif result.action == "sanitize" and result.sanitized_content:
                violations.append(f"{rule.name}: {result.reason}")
                filtered_content = result.sanitized_content
                risk_score = max(risk_score, 0.5)

        # If any violations, return filtered content
        if violations:
            self._metrics["violations"] += 1
            return FilterResult(
                allowed=risk_score < 0.8,
                content=filtered_content,
                violations=violations,
                risk_score=risk_score,
            )

        return FilterResult(
            allowed=True, content=content, violations=[], risk_score=0.0
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get pipeline metrics."""
        return {
            **self._metrics,
            "input_rules": len(self._input_rules),
            "output_rules": len(self._output_rules),
        }


# Global singleton
_security_pipeline: SecurityPipeline | None = None


async def get_security_pipeline() -> SecurityPipeline:
    """Get or create global security pipeline."""
    global _security_pipeline
    if _security_pipeline is None:
        _security_pipeline = SecurityPipeline()
    return _security_pipeline


def reset_security_pipeline() -> None:
    """Reset global security pipeline (for testing)."""
    global _security_pipeline
    _security_pipeline = None
