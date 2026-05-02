"""GAIA SDK adapter + AMD-optimization-aware tier selection.

Two surfaces:

1. **GaiaAgentTier** — wraps an ``amd-gaia`` Agent (or MCPAgent) so it can
   serve as a tier inside a ``TieredOrchestrator``. GAIA's Agent natively
   talks to Lemonade → XDNA 2 NPU, so using GAIA as a tier target picks the
   AMD-optimized path automatically.

2. **amd_optimized_hierarchy()** — factory that prefers AMD-backed tiers
   (FLM on NPU, ROCWMMA on iGPU, AVX-VNNI on CPU) ahead of generic paths.

Reference: amd-gaia 0.17.2 installed (2026-04-18) — see
``/home/mike-anderson/dev/cohezion/.venv/lib/python3.11/site-packages/gaia/``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from cohezion.inference.orchestrator import (
    OrchestrationResult,
    QualityGate,
    TieredOrchestrator,
)
from cohezion.inference.registry import Lane, get_registry


logger = logging.getLogger(__name__)


# Lane-family ranking: lower number = more AMD-silicon-native = preferred.
# This is the "pick paths that unlock AMD optimizations" directive, encoded.
_AMD_PATH_RANK: dict[Lane, int] = {
    Lane.NPU: 0,  # XDNA 2 via FLM — most AMD-native
    Lane.IGPU_ROCWMMA: 1,  # RDNA 3.5 ROCWMMA
    Lane.IGPU_UNIFIED: 1,  # RDNA 3.5 with 120 GB GTT
    Lane.CPU: 2,  # AVX-VNNI via lemonade
    Lane.CLOUD_OLLAMA: 3,  # Generic (non-AMD) cloud
    Lane.CLOUD_GEMINI: 4,
    Lane.CLOUD_CLAUDE: 5,
}


@dataclass
class GaiaAgentTier:
    """Wrap a ``gaia.Agent`` / ``gaia.MCPAgent`` instance as a tier target.

    Usage::

        from gaia import Agent
        from cohezion.inference.orchestrator import TieredOrchestrator, QualityGate
        from cohezion.inference.gaia_adapter import GaiaAgentTier

        gaia_agent = Agent(model_id="Gemma-4-E2B-it-GGUF", silent_mode=True)
        orch = TieredOrchestrator(tiers=[
            (GaiaAgentTier(gaia_agent, label="gaia-e2b"), QualityGate.TRUST),
        ])
    """

    agent: object  # gaia.Agent — kept as `object` to avoid import-time dep
    label: str = "gaia-agent"

    async def run(self, prompt: str, **_: object) -> OrchestrationResult:
        """Invoke the GAIA Agent, wrap its response in OrchestrationResult."""
        start = time.perf_counter()
        ttft: float | None = None
        text = ""
        cost = 0.0
        error: str | None = None

        # GAIA's Agent.prompt() is the public sync surface. Some versions
        # expose .run() — we probe for either. Keep the adapter resilient.
        run_fn = (
            getattr(self.agent, "prompt", None)
            or getattr(self.agent, "run", None)
            or getattr(self.agent, "chat", None)
        )
        if run_fn is None:
            error = "GaiaAgentTier: agent has no prompt/run/chat method"
        else:
            try:
                # GAIA is sync-first; run in default executor to avoid blocking loop
                import asyncio

                loop = asyncio.get_running_loop()
                out = await loop.run_in_executor(None, run_fn, prompt)
                text = out if isinstance(out, str) else str(out)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"

        latency_ms = (time.perf_counter() - start) * 1000
        return OrchestrationResult(
            text=text,
            primary_model=self.label,
            final_model=self.label,
            escalation_count=0,
            tier_path=[],
            cost_usd=cost,
            latency_ms=latency_ms,
            ttft_ms=ttft,
            error=error,
        )


def rank_models_by_amd_optimization(model_ids: list[str]) -> list[str]:
    """Sort model IDs so AMD-native backends come first.

    NPU (FLM) < iGPU (ROCWMMA) < CPU (AVX-VNNI) < Cloud. Within a rank,
    preserve registry priority.
    """
    registry = get_registry()
    keyed: list[tuple[int, int, str]] = []
    for mid in model_ids:
        if mid not in registry.models:
            keyed.append((99, 999, mid))
            continue
        m = registry.models[mid]
        rank = _AMD_PATH_RANK.get(m.lane, 99)
        keyed.append((rank, m.priority, mid))
    keyed.sort()
    return [mid for _, _, mid in keyed]


def amd_optimized_hierarchy(
    *,
    include_cloud: bool = True,
    max_cost_usd: float = 0.05,
) -> TieredOrchestrator:
    """Build an orchestrator that prefers AMD-backed tiers in ascending cost.

    Tier 0: NPU (FLM, most AMD-native) — Gemma-4-E2B
    Tier 1: iGPU ROCWMMA — Gemma-4-E4B
    Tier 2: iGPU Unified (120GB GTT, MoE) — Gemma-4-26B-A4B
    Tier 3: CPU (AVX-VNNI) — Gemma-4-31B
    Tier 4+: Cloud fallback (Claude/Gemini CLI) — only if include_cloud
    """
    tiers: list[tuple[str, QualityGate]] = [
        ("Gemma-4-E2B-it-GGUF", QualityGate(min_chars=15)),
        ("Gemma-4-E4B-it-GGUF", QualityGate(min_chars=25)),
        ("Gemma-4-26B-A4B-it-GGUF", QualityGate(min_chars=40)),
        ("Gemma-4-31B-it-GGUF", QualityGate(min_chars=60)),
    ]
    if include_cloud:
        tiers.append(("claude-haiku-4-5", QualityGate(min_chars=80)))
        tiers.append(("claude-sonnet-4-6", QualityGate.TRUST))  # type: ignore[attr-defined]
    return TieredOrchestrator(
        tiers=tiers,  # type: ignore[arg-type]
        max_cost_usd=max_cost_usd,
    )


def build_gaia_native_tier(
    model_id: str = "Gemma-4-E2B-it-GGUF",
    *,
    silent: bool = True,
    base_url: str | None = "http://localhost:13306/v1",
) -> GaiaAgentTier:
    """Instantiate a GAIA Agent bound to a specific lane, wrap as a tier.

    Uses ``skip_lemonade=True`` so we can pin the dispatch to the specific port.
    """
    try:
        from gaia.agents.chat.agent import ChatAgent, ChatAgentConfig
    except ImportError as exc:
        raise RuntimeError("amd-gaia not installed — `uv pip install amd-gaia`") from exc

    # ChatAgent doesn't pass skip_lemonade through its config, but the base Agent does.
    class FixedChatAgent(ChatAgent):
        def __init__(self, config):
            super().__init__(config=config)
            self.skip_lemonade = True

    config = ChatAgentConfig(
        model_id=model_id,
        base_url=base_url,
        silent_mode=silent,
    )
    agent = FixedChatAgent(config=config)
    return GaiaAgentTier(agent=agent, label=f"gaia:{model_id}")
