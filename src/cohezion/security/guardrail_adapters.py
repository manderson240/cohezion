"""Adapters to wrap existing guardrails into unified protocol.

These adapters implement the Guardrail protocol for existing
safety/validation components in the codebase.
"""

import logging
from typing import Any, ClassVar

from cohezion.core.resource_monitor import get_resource_monitor
from cohezion.security.constitutional_shield import ConstitutionalShield as CoreConstitutionalShield
from cohezion.security.guardrail_pipeline import GuardrailAction, GuardrailResult
from cohezion.security.rate_limiter import get_rate_limiter


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
    Uses the core ConstitutionalShield implementation.
    """

    def __init__(self, safe_threshold: float = 0.7, unsafe_threshold: float = 0.3):
        """Initialize with safety thresholds.

        Args:
            safe_threshold: Score >= this is considered SAFE
            unsafe_threshold: Score < this is considered UNSAFE (incinerated)
        """
        self._shield = CoreConstitutionalShield(
            safe_threshold=safe_threshold,
            unsafe_threshold=unsafe_threshold,
        )

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Check constitutional alignment."""
        # Length check first (fast fail)
        if text and len(text) > 100000:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason="Input exceeds maximum length (100KB)",
                guard_name="constitutional",
            )

        # Use core ConstitutionalShield
        audit = self._shield.audit(text)

        if audit.verdict.value == "incinerated":
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason=f"Content blacklisted: {', '.join(audit.reasons)}",
                guard_name="constitutional",
                metadata={"safety_score": audit.safety_score, "verdict": audit.verdict.value},
            )
        elif audit.verdict.value == "quarantined":
            # Log for Triune review but allow (fail-open)
            logger.warning(
                "Constitutional content quarantined (score=%.2f): %s",
                audit.safety_score,
                audit.reasons,
            )
            return GuardrailResult(
                action=GuardrailAction.ALLOW,
                reason="Content quarantined for review (allowed in fail-open mode)",
                guard_name="constitutional",
                metadata={
                    "safety_score": audit.safety_score,
                    "verdict": "quarantined",
                    "requires_review": True,
                },
            )
        else:
            return GuardrailResult(
                action=GuardrailAction.ALLOW,
                reason=f"Constitutional check passed (score={audit.safety_score:.2f})",
                guard_name="constitutional",
                metadata={"safety_score": audit.safety_score, "verdict": audit.verdict.value},
            )


class PromptInjectionGuard:
    """Adapter for prompt injection detection.

    Detects common prompt injection patterns.
    """

    # Common injection patterns (class-level constant)
    INJECTION_PATTERNS: ClassVar[list[str]] = [
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
    Uses the core ResourceMonitor for actual memory/CPU monitoring.
    """

    def __init__(self, max_concurrent_requests: int = 100):
        """Initialize with capacity limits."""
        self.max_concurrent_requests = max_concurrent_requests
        self.current_requests = 0
        self._monitor = get_resource_monitor()

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Check resource availability."""
        # Simple check: prevent runaway concurrent requests
        if self.current_requests >= self.max_concurrent_requests:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason=(
                    f"System at capacity ({self.current_requests}/{self.max_concurrent_requests})"
                ),
                guard_name="resource",
            )

        # Use core ResourceMonitor for actual memory/CPU monitoring
        stats = self._monitor.get_stats()

        # Check if resources are sufficient
        if not self._monitor.should_rent():
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason=(
                    f"Resources constrained: CPU={stats['cpu_percent']:.1f}%, "
                    f"Memory={stats['memory_percent']:.1f}%"
                ),
                guard_name="resource",
                metadata={"stats": stats},
            )

        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            reason=(
                f"Resources available: CPU={stats['cpu_percent']:.1f}%, "
                f"Memory={stats['memory_percent']:.1f}%"
            ),
            guard_name="resource",
            metadata={"stats": stats},
        )


class RateLimitGuard:
    """Adapter for rate limiting.

    Enforces request quotas per agent/user.
    Uses the core RateLimiter with token bucket algorithm.
    """

    def __init__(self, requests_per_minute: int = 60):
        """Initialize with rate limit."""
        self.requests_per_minute = requests_per_minute
        self._limiter = get_rate_limiter()
        # Set default limit
        self._limiter.set_limit("default", requests_per_minute, 60)

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Check rate limit."""
        # Extract key from context (agent_id, user_id, or IP)
        key = context.get("agent_id") or context.get("user_id") or context.get("ip", "unknown")
        endpoint = context.get("endpoint", "default")

        # Use core RateLimiter
        result = self._limiter.check(key=key, endpoint=endpoint)

        if not result.allowed:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason=f"Rate limit exceeded: {result.remaining}/{result.limit} requests remaining",
                guard_name="rate_limit",
                metadata={
                    "remaining": result.remaining,
                    "limit": result.limit,
                    "reset_after": result.reset_after,
                },
            )

        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            reason=f"Within rate limit: {result.remaining}/{result.limit} requests remaining",
            guard_name="rate_limit",
            metadata={
                "remaining": result.remaining,
                "limit": result.limit,
                "reset_after": result.reset_after,
            },
        )


class OutputFilterGuard:
    """Adapter for output safety validation.

    Checks model output for harmful content.
    """

    # Common harmful patterns in output (class-level constant)
    HARMFUL_PATTERNS: ClassVar[list[str]] = [
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
