"""
Triune Orchestrator: Automated hardware-aware routing for GAIA experiments.
Seamlessly routes complex tasks across NPU, iGPU, and CPU on AMD Strix Halo.
"""

from __future__ import annotations

import logging

from cohezion.inference.gaia_adapter import build_gaia_native_tier
from cohezion.inference.orchestrator import (
    QualityGate,
    TieredOrchestrator,
)


logger = logging.getLogger(__name__)

def build_triune_orchestrator(
    *,
    npu_port: int = 13306,
    igpu_port: int = 13307,
    cpu_port: int = 11434,
) -> TieredOrchestrator:
    """
    Constructs a TieredOrchestrator mapped to the Triune Substrate.
    
    Tiers:
    0. NPU (FastFlowLM): qwen3.5-4b-FLM (Port 13306)
    1. iGPU (TurboKV Wave32): Gemma-4-E4B-it-GGUF (Port 13307)
    2. CPU (Vectorized AVX-512): Gemma-4-31B-it-GGUF (Port 11434)
    """

    # 1. NPU Tier - Initial analytical pass
    npu_tier = build_gaia_native_tier(
        model_id="qwen3.5-4b-FLM",
        base_url=f"http://localhost:{npu_port}/v1",
        silent=True
    )

    # 2. iGPU Tier - Deep context analysis (Wave32 unlocked)
    igpu_tier = build_gaia_native_tier(
        model_id="Gemma-4-E4B-it-GGUF",
        base_url=f"http://localhost:{igpu_port}/v1",
        silent=True
    )

    # 3. CPU Tier - Ultimate fallback reasoning (AVX-512)
    cpu_tier = build_gaia_native_tier(
        model_id="Gemma-4-31B-it-GGUF",
        base_url=f"http://localhost:{cpu_port}/v1",
        silent=True
    )

    return TieredOrchestrator(
        tiers=[
            (npu_tier, QualityGate(min_chars=500)),   # NPU must provide a solid start
            (igpu_tier, QualityGate(min_chars=2000)), # iGPU for complex synthesis
            (cpu_tier, QualityGate.TRUST)             # CPU for guaranteed completion
        ]
    )
