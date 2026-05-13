"""platform-coordinator: cross-platform routing, cost tiers, fallback chains."""

from __future__ import annotations

from cohezion.agents.specialists._base import AgentCard, PlatformSpecialist, register


@register
class PlatformCoordinator(PlatformSpecialist):
    """Top-level coordinator for cross-provider LLM routing and cost enforcement.

    Scope:
        - CostAwareRouter tier policy: 70% simple local, 20% medium Sonnet, 10% hard Opus.
        - Fallback chains: Ollama → Flash-Lite → Sonnet → Opus (automatic within router).
        - BudgetEnforcer monthly-budget guards.
        - Every production LLM call routes through here.
    """

    CARD = AgentCard(
        name="platform-coordinator",
        display_name="Platform Coordinator",
        description=(
            "Coordinates LLM calls across providers (Ollama, Anthropic, Google, Lemonade). "
            "Owns the CostAwareRouter tier policy (70% simple local → 20% medium Sonnet → "
            "10% hard Opus), fallback chains on provider failure, and BudgetEnforcer "
            "monthly-budget guards. Every production LLM call goes through here."
        ),
        role="Cross-platform LLM dispatch + cost enforcement",
        capabilities=(
            "route.llm.tier_dispatch",
            "enforce.llm.budget",
            "manage.llm.fallback_chain",
            "report.llm.cost_observability",
        ),
        principles=(
            ("Every LLM call routes through CostAwareRouter. No direct provider SDK calls in production."),
            ("Fallback chain: Ollama → Flash-Lite → Sonnet → Opus. Automatic within the router, absent on bypass."),
            (
                "Tier policy: 70% simple (free local), 20% medium ($3/M), 10% hard ($15/M). "
                "Drift triggers an alert, not a silent escalation."
            ),
            ("BudgetEnforcer only sees instrumented paths — bypasses are invisible and a reliability bug."),
        ),
        prime_skill_ref="src/cohezion/skills/platform-coordinator.md",
        canonical_modules=(
            "cohezion.swarm.cost_aware_router",
            "cohezion.swarm.adaptive_router",
            "cohezion.swarm.context_model_router",
        ),
    )
