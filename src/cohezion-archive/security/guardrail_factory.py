"""Factory for creating pre-configured guardrail pipelines."""

import logging
from typing import Any

from cohezion.security.guardrail_adapters import (
    ConstitutionalGuard,
    OutputFilterGuard,
    PromptInjectionGuard,
    RateLimitGuard,
    ResourceGuard,
)
from cohezion.security.guardrail_pipeline import GuardrailPipeline


logger = logging.getLogger(__name__)


async def _audit_to_vault(event: dict[str, Any]) -> None:
    """Audit guardrail actions to vault for observability.

    Non-blocking: logs to debug level on failure.
    """
    try:
        # TODO: Wire to cohezion.compound.vault_execution_logger.VaultExecutionLogger
        #       after MCP client is available
        logger.debug(f"Guardrail audit: {event}")
    except Exception as e:
        logger.debug(f"Vault audit failed (non-critical): {e}")


def create_default_pipeline(strict_mode: bool = False) -> GuardrailPipeline:
    """Create standard pipeline with all guards.

    Execution order:
        1. ConstitutionalShield (alignment)
        2. PromptGuard (injection detection)
        3. ResourceGuard (capacity check)
        4. RateLimitGuard (quota check)
        5. OutputFilterGuard (response safety)

    Args:
        strict_mode: If True, block on any exception (fail-closed).
                    If False (default), log and allow (fail-open).

    Returns:
        Configured GuardrailPipeline ready to use.
    """
    guards = [
        ("constitutional", ConstitutionalGuard()),
        ("prompt_injection", PromptInjectionGuard()),
        ("resource", ResourceGuard()),
        ("rate_limit", RateLimitGuard()),
        ("output_filter", OutputFilterGuard()),
    ]

    return GuardrailPipeline(
        guardrails=guards,
        fail_closed=strict_mode,
        audit_callback=_audit_to_vault,
    )


def create_minimal_pipeline() -> GuardrailPipeline:
    """Create lightweight pipeline (injection + output only).

    For latency-sensitive operations.
    """
    guards = [
        ("prompt_injection", PromptInjectionGuard()),
        ("output_filter", OutputFilterGuard()),
    ]

    return GuardrailPipeline(
        guardrails=guards,
        fail_closed=False,
        audit_callback=_audit_to_vault,
    )


def create_strict_pipeline() -> GuardrailPipeline:
    """Create strict pipeline (all guards, fail-closed).

    For security-critical operations.
    """
    return create_default_pipeline(strict_mode=True)
