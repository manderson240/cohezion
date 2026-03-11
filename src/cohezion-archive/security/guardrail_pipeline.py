"""Composable guardrail pipeline for unified LLM safety checks.

Architecture:
    GuardrailPipeline orchestrates multiple guardrails in sequence:
    1. ConstitutionalShield - Alignment verification
    2. PromptGuard - Injection detection
    3. ResourceGuard - Capacity verification
    4. RateLimitGuard - Quota enforcement
    5. OutputFilter - Response safety validation

Execution model:
    - Short-circuit on BLOCK (fail-fast)
    - Sanitization support (modify input in-place)
    - Audit callback for all actions
    - Statistics tracking (allowed/blocked/sanitized)
"""

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


logger = logging.getLogger(__name__)


class GuardrailAction(StrEnum):
    """Action taken by guardrail."""

    ALLOW = "allow"
    BLOCK = "block"
    SANITIZE = "sanitize"
    LOG_AND_ALLOW = "log_and_allow"


@dataclass
class GuardrailResult:
    """Result from a guardrail check."""

    action: GuardrailAction
    reason: str = ""
    modified_input: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    guard_name: str = ""
    latency_ms: float = 0.0


@dataclass
class GuardrailStats:
    """Statistics for guardrail usage."""

    allowed: int = 0
    blocked: int = 0
    sanitized: int = 0
    total_latency_ms: float = 0.0


class Guardrail(Protocol):
    """Protocol for guardrail implementations."""

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Execute guardrail check.

        Args:
            text: Input text to check
            context: Contextual information (skill_name, agent_id, etc.)

        Returns:
            GuardrailResult with action and metadata
        """
        ...


class GuardrailPipeline:
    """Orchestrate multiple guardrails with short-circuit logic.

    Execution order:
        1. ConstitutionalShield (alignment)
        2. PromptGuard (injection)
        3. ResourceGuard (capacity)
        4. RateLimitGuard (quota)
        5. OutputFilter (response safety)

    Features:
        - Short-circuit on BLOCK (fail-fast)
        - Input sanitization support
        - Audit callback for observability
        - Statistics tracking per guardrail
        - Configurable fail-open vs fail-closed
    """

    def __init__(
        self,
        guardrails: list[tuple[str, Guardrail]] | None = None,
        fail_closed: bool = False,
        audit_callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ):
        """Initialize pipeline.

        Args:
            guardrails: List of (name, guardrail) tuples in execution order.
                       If None, defaults to empty pipeline.
            fail_closed: If True, block on any guardrail exception.
                        If False (default), log and allow on exception.
            audit_callback: Async callback for audit logging.
                           Called with {"action": ..., "guard": ..., ...}
        """
        self.guardrails = guardrails or []
        self.fail_closed = fail_closed
        self.audit_callback = audit_callback
        self.stats: dict[str, GuardrailStats] = {
            name: GuardrailStats() for name, _ in self.guardrails
        }

    async def check_input(
        self, text: str, context: dict[str, Any] | None = None
    ) -> GuardrailResult:
        """Check input through all guardrails.

        Runs guardrails in sequence, short-circuits on BLOCK.
        Applies sanitization if needed.

        Args:
            text: Input text to check
            context: Contextual info (skill_name, agent_id, etc.)

        Returns:
            GuardrailResult with final action and modified_input if sanitized
        """
        context = context or {}
        current_text = text
        results: list[GuardrailResult] = []

        for guard_name, guardrail in self.guardrails:
            try:
                start_time = time.time()
                result = await guardrail.check(current_text, context)
                latency_ms = (time.time() - start_time) * 1000
                result.guard_name = guard_name
                result.latency_ms = latency_ms

                # Update stats
                if result.action == GuardrailAction.ALLOW:
                    self.stats[guard_name].allowed += 1
                elif result.action == GuardrailAction.BLOCK:
                    self.stats[guard_name].blocked += 1
                elif result.action == GuardrailAction.SANITIZE:
                    self.stats[guard_name].sanitized += 1
                    if result.modified_input:
                        current_text = result.modified_input
                self.stats[guard_name].total_latency_ms += latency_ms

                results.append(result)

                # Short-circuit on BLOCK
                if result.action == GuardrailAction.BLOCK:
                    await self._audit(
                        {
                            "action": "block",
                            "guard": guard_name,
                            "reason": result.reason,
                            "input_length": len(text),
                            "context": context,
                        }
                    )
                    return result

            except Exception as e:
                logger.exception(f"Guardrail {guard_name} raised exception")
                if self.fail_closed:
                    return GuardrailResult(
                        action=GuardrailAction.BLOCK,
                        reason=f"Guardrail exception: {guard_name}",
                        guard_name=guard_name,
                    )
                else:
                    # Log and allow
                    await self._audit(
                        {
                            "action": "log_and_allow",
                            "guard": guard_name,
                            "reason": f"Exception: {e!s}",
                        }
                    )

        # All guardrails passed
        final_result = GuardrailResult(
            action=GuardrailAction.ALLOW,
            modified_input=current_text if current_text != text else None,
            reason="All guardrails passed",
        )
        await self._audit({"action": "allow", "guards": len(self.guardrails)})
        return final_result

    async def check_output(
        self, text: str, context: dict[str, Any] | None = None
    ) -> GuardrailResult:
        """Check output through guardrails.

        Simplified flow for response validation (no sanitization).

        Args:
            text: Output text to check
            context: Contextual info

        Returns:
            GuardrailResult
        """
        context = context or {}

        for guard_name, guardrail in self.guardrails:
            try:
                result = await guardrail.check(text, context | {"check_type": "output"})

                if result.action == GuardrailAction.BLOCK:
                    await self._audit(
                        {
                            "action": "block_output",
                            "guard": guard_name,
                            "reason": result.reason,
                        }
                    )
                    return result

            except Exception:
                logger.exception(f"Output guardrail {guard_name} raised exception")
                if self.fail_closed:
                    return GuardrailResult(
                        action=GuardrailAction.BLOCK,
                        reason=f"Output validation exception: {guard_name}",
                        guard_name=guard_name,
                    )

        return GuardrailResult(action=GuardrailAction.ALLOW, reason="Output validated")

    async def _audit(self, event: dict[str, Any]) -> None:
        """Call audit callback if configured."""
        if self.audit_callback:
            try:
                await self.audit_callback(event)
            except Exception:
                logger.exception("Audit callback failed")

    def get_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all guardrails."""
        return {
            name: {
                "allowed": self.stats[name].allowed,
                "blocked": self.stats[name].blocked,
                "sanitized": self.stats[name].sanitized,
                "total_latency_ms": self.stats[name].total_latency_ms,
                "avg_latency_ms": (
                    self.stats[name].total_latency_ms
                    / (
                        self.stats[name].allowed
                        + self.stats[name].blocked
                        + self.stats[name].sanitized
                    )
                    if (
                        self.stats[name].allowed
                        + self.stats[name].blocked
                        + self.stats[name].sanitized
                    )
                    > 0
                    else 0
                ),
            }
            for name in self.stats
        }

    def reset_stats(self) -> None:
        """Reset all statistics."""
        for name in self.stats:
            self.stats[name] = GuardrailStats()
