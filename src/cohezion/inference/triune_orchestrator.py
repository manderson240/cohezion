"""
Triune Orchestrator: Automated hardware-aware routing for GAIA experiments.
Seamlessly routes complex tasks across NPU, iGPU, and CPU on AMD Strix Halo.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cohezion.config.defaults import tier0_model, tier2_model
from cohezion.inference.gaia_adapter import build_gaia_llm_tier, build_gaia_native_tier
from cohezion.inference.orchestrator import (
    QualityGate,
    TieredOrchestrator,
)


if TYPE_CHECKING:
    from cohezion.inference.direct_tier import ParallelFleetOrchestrator


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
    npu_port: int = 13305,
    igpu_port: int = 13305,
    cpu_port: int = 13305,
    enforce_memory_gate: bool = False,
) -> TieredOrchestrator:
    """
    Constructs a TieredOrchestrator mapped to the Triune Substrate.

    Tiers:
    0. NPU (FastFlowLM): llama3.2-1b-FLM (Port 13306, 42 TPS — NOT qwen3.5-4b-FLM)
    1. iGPU (RDNA3.5): Gemma-4-E4B-it-GGUF (Port 13307)
    2. CPU (AVX-512 / lemonade): Gemma-4-31B-it-GGUF (Port 13309)
    """

    # OOM1: gate the heavy CPU reasoner on free RAM (N3/K1). Opt-in via
    # enforce_memory_gate so the default remains a deterministic 3-tier cascade.
    # MemorySnapshot is a lightweight /proc/meminfo form of MemorySnapshot.capture()
    available_gb = None
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    kb = int(line.split()[1])
                    available_gb = kb / (1024 * 1024)
                    break
    except Exception:
        pass
    logger.debug("OOM1 gate: available_gb=%s", available_gb)
    if enforce_memory_gate and available_gb is not None and available_gb < 8.0:
        raise RuntimeError(f"OOM1 invariant violated: available_gb={available_gb} < 8.0 GB")

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


# Tier-0 generation budget (ctx 4096 recipe): see the builder below.
_TIER0_MAX_TOKENS = 2048


def build_triune_omni_orchestrator(
    *, base_url: str = "http://localhost:13305/api/v1"
) -> TieredOrchestrator:
    """OmniRouter cascade — tier 0 → Gemma-4-E4B (iGPU) → tier 2, deduplicated by model id,
    ALL served by the single :13305 OmniRouter via the supported GAIA ``LemonadeClient`` path
    (:func:`build_gaia_llm_tier`).

    N1: :13305 is the only port needed — the dedicated per-port servers (:13306/:13307/:13309) are
    redundant and often offline, so this OmniRouter variant is the default ``exec_provider`` for the
    compound loop (``make_executor``).

    2026-07-09: the CPU tier previously used ``Gemma-4-31B-it-GGUF``, which the router places on
    Vulkan (iGPU) — a FAKE CPU tier (two tiers on one device) that was also too slow (>236s).

    2026-10-24: tier 0 is NPU-first (``config.defaults.tier0_model``, default
    ``gemma4-it-e2b-FLM``, ctx from its saved lemonade recipe only; 1.000 on the calibrated
    gauntlet with think=false). It is the ONE shared NPU model (single slot), and FLM's think
    flag is sticky on the loaded model, so ``build_gaia_llm_tier`` sends every tier-0 request
    ``think: false`` (``config.defaults.tier0_request_extras``).

    Tier 2 is ``config.defaults.tier2_model`` (``COHEZION_TIER2_MODEL``) and tiers are
    DEDUPLICATED by model id, first occurrence wins (lemonade keeps one instance and one saved
    option set per id, so a repeat is a resample, not a tier). The tier-2 default is the E4B
    id, so the default cascade is ``[gemma4-it-e2b-FLM, Gemma-4-E4B]`` -- the iGPU only as the
    quality-gate escalation. A more capable tier 2 AWAITS THE LARGE-MODEL SWEEP; set the
    env var to add one. Whatever tier ends up last carries the TRUST gate, so the cascade always
    completes (tasks complete > quality > speed).

    KNOWN FOLLOW-UP (engine attribution): ``local_inference._engine_for`` clamps to its own
    3-entry ``_OMNI_TIERS``, not to this cascade's length. With the default two tiers a
    confident "cpu" prediction (entry index 2) runs on E4B -- the orchestrator clamps the entry
    to the last tier -- but ``_engine_for(2, 0)`` still reports "cpu", so DifficultyEstimator
    attributes those E4B runs to "cpu". Fix by clamping with the real tier count.
    """
    # Tier-0 budget: with think=false the FLM default answers directly, but the Gemma-4-E2B GGUF
    # override is a thinking model whose inline CoT (reasoning_format="none") would truncate at
    # the 512 default and then escalate on budget, not quality. Both recipes serve ctx 4096:
    # 2048 generated tokens leave ~2048 tokens of prompt room.
    specs: list[tuple[str, int | None, QualityGate]] = [
        (tier0_model(), _TIER0_MAX_TOKENS, QualityGate(min_chars=500)),  # solid start
        ("Gemma-4-E4B-it-GGUF", None, QualityGate(min_chars=2000)),  # iGPU complex synthesis
        (tier2_model(), None, QualityGate.TRUST),  # guaranteed completion
    ]
    seen: set[str] = set()
    unique: list[tuple[str, int | None, QualityGate]] = []
    for model_id, max_tokens, gate in specs:
        if model_id in seen:
            continue  # one lemonade instance per id: a repeat is a resample, not a tier
        seen.add(model_id)
        unique.append((model_id, max_tokens, gate))
    # The last surviving tier completes the cascade, whatever was deduplicated after it.
    unique[-1] = (unique[-1][0], unique[-1][1], QualityGate.TRUST)

    tiers = []
    for model_id, max_tokens, gate in unique:
        kwargs = {"max_tokens": max_tokens} if max_tokens is not None else {}
        tier = build_gaia_llm_tier(model_id=model_id, base_url=base_url, silent=True, **kwargs)
        tiers.append((tier, gate))
    return TieredOrchestrator(tiers=tiers)


def build_reasoning_orchestrator(
    *,
    omni_port: int = 13305,
) -> TieredOrchestrator:
    """Reasoning-optimized orchestrator using qwen3.6-moe-35b-a3b-FLM on the NPU.

    Lane history: deepseek-r1-0528-8b-FLM held this tier from 2026-06-22. Replaced
    2026-08-03 on fixture-sweep evidence (lap 80303, n=52/arm, deterministic graders):
    qwen3.6-moe 0.942 overall / 1.000 reasoning-role vs deepseek 0.635 / 0.058 —
    model_performance rows in SurrealDB (cohezion:main), report
    vault reports/20260803-qwen36-three-lane-eval.md. qwen is content-channel-only
    (no <think> trap) and ~9-10 TPS on XDNA2.

    All tiers talk to the OmniRouter (:13305) via GAIA SDK — no per-port servers needed.

    Tiers:
    0. NPU reasoning: qwen3.6-moe-35b-a3b-FLM (:13305, ~9.7 TPS, XDNA2 FLM MoE)
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
        model_id="qwen3.6-moe-35b-a3b-FLM",
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
