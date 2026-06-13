"""gemini-specialist: Gemini CLI + Google ADK + Gemma 4 provider specialist."""

from __future__ import annotations

from cohezion.agents.specialists._base import AgentCard, PlatformSpecialist, register


@register
class GeminiSpecialist(PlatformSpecialist):
    """Owns the Google ecosystem integration.

    Scope:
        - Gemini CLI, Google ADK (``google-adk`` dependency).
        - Gemma 4 provider used by the EcoResilience agent.
        - Flash-Lite tier routing in CostAwareRouter.
    """

    CARD = AgentCard(
        name="gemini-specialist",
        display_name="Gemini Specialist",
        description=(
            "Owns Google ecosystem integration: Gemini CLI, Google ADK, and the Gemma 4 "
            "provider used by the EcoResilience agent. Tracks Flash-Lite tier routing in "
            "CostAwareRouter and Google-specific prompt idioms."
        ),
        role="Google ADK + Gemini integration expert",
        capabilities=(
            "configure.google_adk",
            "route.gemini.flash_lite",
            "manage.gemma4.provider",
        ),
        principles=(
            "Google API credentials come from the vault, never from shell history.",
            (
                "Flash-Lite is the medium-tier default in CostAwareRouter — do not route simple tasks to Pro."
            ),
            "Local Gemma 4 provider is preferred for Google-flavored prompts when available.",
        ),
        prime_skill_ref="src/cohezion/skills/gemini-specialist.md",
        canonical_modules=("cohezion.swarm.providers.gemma4_provider",),
    )
