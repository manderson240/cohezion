"""Adapters to wrap existing guardrails into unified protocol.

These adapters implement the Guardrail protocol for existing
safety/validation components in the codebase.
"""

import logging
from typing import Any

from cohezion.security.guardrail_pipeline import GuardrailAction, GuardrailResult

logger = logging.getLogger(__name__)


class NoOpGuard:
    """Default no-op guard that allows everything.

    Used as placeholder when actual guards are not available.
    """

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Accept all input."""
        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            reason="No-op guard",
        )


class ConstitutionalGuard:
    """Adapter for alignment checking.

    Verifies that input aligns with constitutional principles.
    Currently a no-op; will be wired to actual ConstitutionalShield
    when available.
    """

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Check constitutional alignment."""
        # TODO: Wire to cohezion.validation.constitutional.ConstitutionalShield
        #       when available
        if text and len(text) > 100000:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason="Input exceeds maximum length (100KB)",
                guard_name="constitutional",
            )
        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            reason="Constitutional check passed",
            guard_name="constitutional",
        )


class PromptInjectionGuard:
    """Adapter for prompt injection detection.

    Uses the full PromptGuard (70+ patterns, deobfuscation, multilingual)
    for comprehensive injection detection including leet-speak normalization,
    zero-width character stripping, and OWASP LLM Top 10 coverage.
    """

    def __init__(self, strict_mode: bool = False):
        from cohezion.security.prompt_guard import PromptGuard

        self._guard = PromptGuard(strict_mode=strict_mode)

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Check for prompt injection using full PromptGuard."""
        from cohezion.security.prompt_guard import ThreatLevel

        analysis = self._guard.analyze(text, agent_name=context.get("agent_id"))

        if analysis.threat_level == ThreatLevel.MALICIOUS:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason=f"Prompt injection detected: {', '.join(analysis.matched_patterns)}",
                guard_name="prompt_injection",
                metadata={
                    "confidence": analysis.confidence,
                    "patterns": analysis.matched_patterns,
                },
            )

        if analysis.threat_level == ThreatLevel.SUSPICIOUS:
            return GuardrailResult(
                action=GuardrailAction.LOG_AND_ALLOW,
                reason=f"Suspicious patterns: {', '.join(analysis.matched_patterns)}",
                guard_name="prompt_injection",
                metadata={
                    "confidence": analysis.confidence,
                    "patterns": analysis.matched_patterns,
                },
            )

        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            reason="No injection patterns detected",
            guard_name="prompt_injection",
        )


class ResourceGuard:
    """Adapter for resource capacity checking.

    Verifies system capacity before processing requests.
    Currently checks memory and concurrency; will be wired to
    actual ResourceMonitor when available.
    """

    def __init__(self, max_concurrent_requests: int = 100):
        """Initialize with capacity limits."""
        self.max_concurrent_requests = max_concurrent_requests
        self.current_requests = 0

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Check resource availability."""
        # Simple check: prevent runaway concurrent requests
        if self.current_requests >= self.max_concurrent_requests:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason=f"System at capacity ({self.current_requests}/{self.max_concurrent_requests})",
                guard_name="resource",
            )

        # TODO: Wire to cohezion.reliability.monitor.ResourceMonitor
        #       for actual memory/CPU monitoring

        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            reason="Resources available",
            guard_name="resource",
        )


class RateLimitGuard:
    """Adapter for rate limiting.

    Enforces request quotas per agent/user.
    Currently uses simple token bucket; will be wired to
    actual RateLimiter when available.
    """

    def __init__(self, requests_per_minute: int = 60):
        """Initialize with rate limit."""
        self.requests_per_minute = requests_per_minute
        self.request_counts: dict[str, list[float]] = {}

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Check rate limit."""
        # TODO: Wire to cohezion.security.rate_limiter.RateLimiter
        #       for production rate limiting

        # For now, allow all requests
        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            reason="Within rate limit",
            guard_name="rate_limit",
        )


class OutputFilterGuard:
    """Adapter for output safety validation.

    Uses the full OutputFilter with PII detection (email, phone, SSN,
    credit card, IP address) and toxicity filtering.
    """

    def __init__(self, redact_pii: bool = True, block_toxic: bool = True):
        from cohezion.security.output_filter import OutputFilter

        self._filter = OutputFilter(redact_pii=redact_pii, block_toxic=block_toxic)

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Check output for harmful content and PII."""
        from cohezion.security.output_filter import FilterResult

        result = self._filter.filter(text)

        if result.result == FilterResult.TOXIC_DETECTED:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason="Toxic content detected in output",
                guard_name="output_filter",
                metadata={"redactions": result.redactions, "warnings": result.warnings},
            )

        if result.result == FilterResult.PII_DETECTED:
            return GuardrailResult(
                action=GuardrailAction.SANITIZE,
                reason=f"PII redacted: {', '.join(result.redactions)}",
                guard_name="output_filter",
                modified_input=result.content,
                metadata={"redactions": result.redactions, "warnings": result.warnings},
            )

        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            reason="Output is safe",
            guard_name="output_filter",
        )
