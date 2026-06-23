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


def build_triune_orchestrator(
    *,
    npu_port: int = 13306,
    igpu_port: int = 13307,
    cpu_port: int = 13309,  # N2: lemonade CPU port (NOT 11434/Ollama — migrated 2026-05-21)
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

    # 3. CPU Tier — lemonade :13309 (AVX-512); N2: NOT Ollama :11434
    cpu_tier = build_gaia_native_tier(
        model_id="Gemma-4-31B-it-GGUF", base_url=f"http://localhost:{cpu_port}/v1", silent=True
    )

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
    1. iGPU synthesis: Gemma-4-E4B-it-GGUF (:13305, RDNA3.5)
    2. CPU completion: Gemma-4-31B-it-GGUF (:13305, AVX-512)
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
    cpu_completion = build_gaia_llm_tier(
        model_id="Gemma-4-31B-it-GGUF",
        base_url=base_url,
        max_tokens=4096,
        silent=True,
    )

    return TieredOrchestrator(
        tiers=[
            (npu_reasoning, QualityGate(min_chars=100)),
            (igpu_synthesis, QualityGate(min_chars=1000)),
            (cpu_completion, QualityGate.TRUST),
        ]
    )
