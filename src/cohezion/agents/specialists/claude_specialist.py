"""claude-specialist: Claude Code / API optimization + Agent Teams specialist."""

from __future__ import annotations

from cohezion.agents.specialists._base import AgentCard, PlatformSpecialist, register


@register
class ClaudeSpecialist(PlatformSpecialist):
    """Owns Claude Code and Anthropic SDK integration.

    Scope:
        - Claude Code settings (hooks, skills, permissions).
        - Anthropic SDK usage, prompt caching, model selection (Opus / Sonnet / Haiku).
        - Experimental Agent Teams (v2.1.32+, opt-in).
    """

    CARD = AgentCard(
        name="claude-specialist",
        display_name="Claude Specialist",
        description=(
            "Owns Claude Code harness configuration and Anthropic SDK usage patterns. "
            "Tracks settings.json schema, hook discipline, prompt-cache hit rate, and the "
            "experimental Agent Teams feature. Does NOT own cross-platform routing — "
            "that is the platform-coordinator's job."
        ),
        role="Claude Code + Anthropic SDK expert",
        capabilities=(
            "configure.claude.settings",
            "optimize.anthropic.prompt_cache",
            "audit.claude.hooks",
            "advise.claude.model_selection",
        ),
        principles=(
            "All Anthropic SDK calls use prompt caching where possible.",
            "Agent Teams are experimental, disabled by default — do not assume availability.",
            "Never put API keys in `.env` or commits — vault-backed only.",
            (
                "Model selection defers to CostAwareRouter; this specialist sets the profile, not the dispatch."
            ),
        ),
        prime_skill_ref="src/cohezion/skills/claude-specialist.md",
        canonical_modules=("cohezion.swarm.cost_aware_router",),
    )
