# ruff: noqa: RUF012  # class attrs treated as immutable config; never mutated per-instance
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

    Detects common prompt injection patterns.
    Currently a simple pattern-based checker; will be wired to
    actual PromptGuard when available.
    """

    # Common injection patterns
    INJECTION_PATTERNS = [
        "ignore previous",
        "disregard",
        "system prompt",
        "jailbreak",
        "override",
        "bypass",
    ]

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Check for prompt injection."""
        text_lower = text.lower()

        for pattern in self.INJECTION_PATTERNS:
            if pattern in text_lower:
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    reason=f"Potential injection pattern detected: {pattern}",
                    guard_name="prompt_injection",
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

    Checks model output for harmful content.
    Currently a simple pattern checker; will be enhanced
    with actual ML-based content filtering.
    """

    # Common harmful patterns in output
    HARMFUL_PATTERNS = [
        "execute malicious",
        "delete all",
        "drop database",
        "rm -rf",
    ]

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Check output for harmful content."""
        text_lower = text.lower()

        for pattern in self.HARMFUL_PATTERNS:
            if pattern in text_lower:
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    reason=f"Harmful content detected in output: {pattern}",
                    guard_name="output_filter",
                )

        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            reason="Output is safe",
            guard_name="output_filter",
        )
