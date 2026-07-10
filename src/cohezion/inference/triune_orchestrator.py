"""
Triune Orchestrator: Automated hardware-aware routing for GAIA experiments.
Seamlessly routes complex tasks across NPU, iGPU, and CPU on AMD Strix Halo.
"""

from __future__ import annotations

import logging

from cohezion.inference.gaia_adapter import build_gaia_llm_tier, build_gaia_native_tier
from cohezion.inference.orchestrator import (
    QualityGate,
    TieredOrchestrator,
)


logger = logging.getLogger(__name__)


# OOM1 (harness N3/K1/N2): footprint of the heavy CPU reasoner tier and the RAM
# headroom to keep after a load. The router pre-loads this model; a load that
# exceeds free memory risks the OOM killer (N3), so gate before adding the tier.
_CPU_REASONER_FOOTPRINT_GB = 20.0
_MEMORY_SAFETY_BUFFER_GB = 16.0


def _cpu_reasoner_tier_fits() -> tuple[bool, str]:
    """OOM gate for the heavy CPU reasoner tier (harness N3/K1/N2).

    Mirrors ``ResourceGuard.can_load_model``: reads live free RAM via
    ``MemorySnapshot.capture()`` and refuses the tier when the reasoner
    footprint + safety buffer would exceed available memory, so a load can never
    push the box into the OOM killer. Fails open (allows) if the probe raises.
    """
    try:
        from cohezion.competition.orchestrator.resource_guard import MemorySnapshot

        snap = MemorySnapshot.capture()
    except Exception as exc:  # probe unavailable — do not silently block
        return True, f"memory probe failed ({exc}); gate skipped"

    needed = _CPU_REASONER_FOOTPRINT_GB + _MEMORY_SAFETY_BUFFER_GB
    if snap.available_gb < needed:
        return False, (
            f"CPU reasoner ~{_CPU_REASONER_FOOTPRINT_GB:.0f}GB + "
            f"{_MEMORY_SAFETY_BUFFER_GB:.0f}GB buffer = {needed:.0f}GB > "
            f"{snap.available_gb:.1f}GB free — escalate to router/cloud instead"
        )
    return True, f"fits: {needed:.0f}GB needed <= {snap.available_gb:.1f}GB free"


def build_triune_orchestrator(
    *,
    npu_port: int = 13306,  # allow-direct-port: N2-retained default, not dispatch bypass
    igpu_port: int = 13307,  # allow-direct-port: N2-retained default, not dispatch bypass
    cpu_port: int = 13309,  # N2: lemonade CPU port (NOT 11434/Ollama — migrated 2026-05-21)
    enforce_memory_gate: bool = False,
) -> TieredOrchestrator:
    """
    Constructs a TieredOrchestrator mapped to the Triune Substrate.

    Tiers:
    0. NPU (FastFlowLM): llama3.2-1b-FLM (Port 13306, 42 TPS — NOT qwen3.5-4b-FLM)
    1. iGPU (RDNA3.5): Gemma-4-E4B-it-GGUF (Port 13307)
    2. CPU (AVX-512 / lemonade): Gemma-4-31B-it-GGUF (Port 13309)
    """

    # 1. NPU Tier — N1: llama3.2-1b-FLM only; qwen3.5-4b-FLM is 5x slower on XDNA2
    npu_tier = build_gaia_native_tier(
        model_id="llama3.2-1b-FLM", base_url=f"http://localhost:{npu_port}/v1", silent=True
    )

    # 2. iGPU Tier - Deep context analysis (Wave32 unlocked)
    igpu_tier = build_gaia_native_tier(
        model_id="Gemma-4-E4B-it-GGUF", base_url=f"http://localhost:{igpu_port}/v1", silent=True
    )

    tiers = [
        (npu_tier, QualityGate(min_chars=500)),  # NPU must provide a solid start
        (igpu_tier, QualityGate(min_chars=2000)),  # iGPU for complex synthesis
    ]

    # 3. CPU Tier — lemonade :13309 (AVX-512); N2: NOT Ollama :11434.
    # OOM1: gate the heavy CPU reasoner on free RAM (N3/K1). Opt-in via
    # enforce_memory_gate so the default remains a deterministic 3-tier cascade
    # (an always-on gate would make this pure constructor read live RAM and flake
    # the tier-count contract); enable on memory-tight hosts to escalate rather
    # than risk an OOM hang.
    include_cpu = True
    if enforce_memory_gate:
        include_cpu, reason = _cpu_reasoner_tier_fits()
        if not include_cpu:
            logger.warning("OOM guard: omitting CPU reasoner tier — %s", reason)

    if include_cpu:
        cpu_tier = build_gaia_native_tier(
            model_id="Gemma-4-31B-it-GGUF", base_url=f"http://localhost:{cpu_port}/v1", silent=True
        )
        tiers.append((cpu_tier, QualityGate.TRUST))  # CPU for guaranteed completion

    return TieredOrchestrator(tiers=tiers)


def build_triune_omni_orchestrator(
    *, base_url: str = "http://localhost:13305/api/v1"
) -> TieredOrchestrator:
    """OmniRouter triune cascade — llama3.2 (NPU) → Gemma-4-E4B (iGPU) → Gemma-4-E2B (CPU),
    ALL served by the single :13305 OmniRouter via the supported GAIA ``LemonadeClient`` path
    (:func:`build_gaia_llm_tier`).

    N1: :13305 is the only port needed — the dedicated per-port servers (:13306/:13307/:13309) are
    redundant and often offline, so this OmniRouter variant is the default ``exec_provider`` for the
    compound loop (``make_executor``). Same gates/escalation as the per-port build.

    2026-07-09 fix: the CPU tier previously used ``Gemma-4-31B-it-GGUF``, which the router
    places on Vulkan (iGPU) — a FAKE CPU tier (two tiers on one device) that was also too slow
    (>236s). It now uses ``Gemma-4-E2B-it-GGUF`` loaded with ``llamacpp_backend=cpu`` (persisted
    via ``save_options``), which measurably runs on the Zen5 cores — verified by CPU busy-time
    (~195 core-s vs ~51 on iGPU vs ~9 on NPU for the same request). The three tiers now genuinely
    span three distinct compute substrates, so the cascade parallelises across NPU/iGPU/CPU
    instead of serialising two tiers on the iGPU.
    """
    npu_tier = build_gaia_llm_tier(model_id="llama3.2-1b-FLM", base_url=base_url, silent=True)
    igpu_tier = build_gaia_llm_tier(model_id="Gemma-4-E4B-it-GGUF", base_url=base_url, silent=True)
    cpu_tier = build_gaia_llm_tier(model_id="Gemma-4-E2B-it-GGUF", base_url=base_url, silent=True)
    return TieredOrchestrator(
        tiers=[
            (npu_tier, QualityGate(min_chars=500)),  # NPU must provide a solid start
            (igpu_tier, QualityGate(min_chars=2000)),  # iGPU for complex synthesis
            (cpu_tier, QualityGate.TRUST),  # CPU for guaranteed completion
        ]
    )


def build_reasoning_orchestrator(
    *,
    omni_port: int = 13305,
) -> TieredOrchestrator:
    """Reasoning-optimized orchestrator using deepseek-r1-0528-8b-FLM on the NPU.

    Discovered 2026-06-22: deepseek-r1-0528-8b-FLM lives in the fleet at 10.6 TPS
    on XDNA2 but was never wired. Routes reasoning tasks through NPU before iGPU/CPU.

    All tiers talk to the OmniRouter (:13305) via GAIA SDK — no per-port servers needed.

    Tiers:
    0. NPU reasoning: deepseek-r1-0528-8b-FLM (:13305, 10.6 TPS, XDNA2 FLM)
    1. iGPU synthesis: Gemma-4-E4B-it-GGUF (:13305, RDNA3.5, Vulkan, min_chars=200)
    2. CPU completion: Gemma-4-E4B-it-GGUF (:13305, TRUST gate — fallback or JEPA REROUTE path)

    Note: all models use Vulkan (unified memory) on Strix Halo — there is no physical CPU
    tier. "CPU" here means the heavier fallback in quality order. Gemma-4-31B-it-GGUF is
    excluded because it is too slow on this hardware for compound loop cadence (>236s per
    request) and blocks other Vulkan models during generation. Bonsai-8B gives equivalent
    code-analysis quality at 4x lower latency (<60s).

    iGPU quality gate is min_chars=200 (was 1000). The old threshold forced every concise
    correct answer (~200-500 chars) to escalate to the CPU tier unnecessarily.
    """
    base_url = f"http://localhost:{omni_port}/api/v1"

    npu_reasoning = build_gaia_llm_tier(
        model_id="deepseek-r1-0528-8b-FLM",
        base_url=base_url,
        max_tokens=2048,
        silent=True,
    )
    igpu_synthesis = build_gaia_llm_tier(
        model_id="Gemma-4-E4B-it-GGUF",
        base_url=base_url,
        max_tokens=2048,
        silent=True,
    )
    # Tier 2: E4B again with TRUST gate. Bonsai-8B-gguf returns "No model loaded" 500s
    # (async load race in OmniRouter backend). E4B is confirmed resident and fast (<15s).
    # Duplicating E4B at tier 2 provides a TRUST fallback for JEPA REROUTE escalations
    # (2026-07-02: Beta(2,2) prior in LemonadeWorldModel smooths raw 0.010→0.470 → still
    # REROUTE but min_tier_index=1 now, not 2). Both tier 1 and 2 are E4B — no regression.
    e4b_trust_fallback = build_gaia_llm_tier(
        model_id="Gemma-4-E4B-it-GGUF",
        base_url=base_url,
        max_tokens=2048,
        silent=True,
    )

    return TieredOrchestrator(
        tiers=[
            (npu_reasoning, QualityGate(min_chars=100)),
            (igpu_synthesis, QualityGate(min_chars=200)),
            (e4b_trust_fallback, QualityGate.TRUST),
        ]
    )


def build_parallel_fleet_orchestrator(
    *,
    omni_port: int = 13305,
) -> ParallelFleetOrchestrator:
    """Factory for ParallelFleetOrchestrator — fan-out to NPU/iGPU/CPU simultaneously.

    All three nodes talk to the OmniRouter (:13305).
    """
    from cohezion.inference.direct_tier import ParallelFleetOrchestrator

    return ParallelFleetOrchestrator(omni_port=omni_port)
