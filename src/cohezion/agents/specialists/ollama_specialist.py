"""ollama-specialist: local model lifecycle, VRAM, DynamicModelRouter."""

from __future__ import annotations

from cohezion.agents.specialists._base import AgentCard, PlatformSpecialist, register


@register
class OllamaSpecialist(PlatformSpecialist):
    """Owns local Ollama model lifecycle and VRAM discipline.

    Scope:
        - Ollama process lifecycle on Strix Halo (AMD Radeon 8060S iGPU, 128 GiB unified).
        - Global 4-concurrent-model limit (enforced by DynamicModelRouter).
        - VRAM budget discipline (GPU allocations steal from the same pool as CPU).
        - Local-first cost tier (70% of traffic).
    """

    CARD = AgentCard(
        name="ollama-specialist",
        display_name="Ollama Specialist",
        description=(
            "Owns local model serving: Ollama process lifecycle, VRAM ceilings, "
            "DynamicModelRouter policy, and the 4-concurrent-model global limit. On "
            "Strix Halo (128 GiB unified), GPU allocations steal from the same pool as CPU — "
            "this specialist enforces the budget."
        ),
        role="Local LLM serving expert",
        capabilities=(
            "manage.ollama.lifecycle",
            "enforce.ollama.concurrent_limit",
            "route.ollama.model_selection",
            "monitor.vram.unified_memory",
        ),
        principles=(
            "Global limit: 4 concurrent Ollama models. DynamicModelRouter enforces this.",
            (
                "Unified memory ceiling: 16 GiB per model allocation — "
                "check `torch.cuda.memory_reserved()` before large loads."
            ),
            (
                "Ollama calls on CPU-only systems require `stream=True` "
                "(see `ollama-cpu-streaming-timeout` skill)."
            ),
            "Prefer local Ollama over cloud API calls for tier-1 (70%) tasks.",
        ),
        prime_skill_ref="src/cohezion/skills/ollama-specialist.md",
        canonical_modules=(
            "cohezion.swarm.cost_aware_router",
            "cohezion.swarm.compute_backend_router",
        ),
    )
