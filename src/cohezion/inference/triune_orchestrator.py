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
    npu_base_url: str = "http://localhost:13306",
    igpu_base_url: str = "http://localhost:13307",
    cpu_base_url: str = "http://localhost:13309",
    # Legacy int-port params kept for callers that pass positional port numbers.
    # When these are supplied they override the base_url equivalents.
    npu_port: int | None = None,
    igpu_port: int | None = None,
    cpu_port: int | None = None,
) -> TieredOrchestrator:
    """
    Constructs a TieredOrchestrator mapped to the Triune Substrate.

    Tiers:
    0. NPU (FastFlowLM): llama3.2-1b-FLM (Port 13306)
    1. iGPU (ROCWMMA): Gemma-4-E4B-it-GGUF (Port 13307)
    2. CPU (AVX-512 / Lemonade): Gemma-4-31B-it-GGUF (Port 13309)

    Pass ``base_url`` kwargs to redirect individual tiers to alternate hosts/ports.
    The ``cpu_port`` default is 13309 (Lemonade), NOT 11434 (Ollama) — migrated 2026-05-21.
    """
    if npu_port is not None:
        npu_base_url = f"http://localhost:{npu_port}"
    if igpu_port is not None:
        igpu_base_url = f"http://localhost:{igpu_port}"
    if cpu_port is not None:
        cpu_base_url = f"http://localhost:{cpu_port}"

    # 1. NPU Tier — Initial analytical pass (llama3.2-1b-FLM, XDNA2, 42 TPS)
    npu_tier = build_gaia_native_tier(
        model_id="llama3.2-1b-FLM",
        base_url=f"{npu_base_url}/v1",
        silent=True,
    )

    # 2. iGPU Tier — Deep context analysis (Gemma-4-E4B, ROCWMMA)
    igpu_tier = build_gaia_native_tier(
        model_id="Gemma-4-E4B-it-GGUF",
        base_url=f"{igpu_base_url}/v1",
        silent=True,
    )

    # 3. CPU Tier — Ultimate fallback reasoning (Gemma-4-31B, AVX-512)
    cpu_tier = build_gaia_native_tier(
        model_id="Gemma-4-31B-it-GGUF",
        base_url=f"{cpu_base_url}/v1",
        silent=True,
    )

    return TieredOrchestrator(
        tiers=[
            (npu_tier, QualityGate(min_chars=500)),  # NPU must provide a solid start
            (igpu_tier, QualityGate(min_chars=2000)),  # iGPU for complex synthesis
            (cpu_tier, QualityGate.TRUST),  # type: ignore[attr-defined]  # CPU for guaranteed completion
        ]
    )
