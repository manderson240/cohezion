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
from cohezion.inference.task_classifier import classify as classify_task


logger = logging.getLogger(__name__)


def build_triune_orchestrator(
    *,
    npu_port: int = 13306,
    igpu_port: int = 13307,
    cpu_port: int = 11434,
    clasp_draft_port: int | None = 13308,
) -> TieredOrchestrator:
    """
    Constructs a TieredOrchestrator mapped to the Triune Substrate.

    Tiers:
    0. NPU (FastFlowLM): llama3.2-1b-FLM (Port 13306) — fits in XDNA2 SRAM, 42 TPS
    1. iGPU (CLaSp/TurboKV Wave32): Gemma-4-E4B-it-GGUF (Port 13307)
       With CLaSp: draft via Gemma-4-E2B-it-GGUF (Port 13308, optional)
    2. CPU (Vectorized AVX-512): Gemma-4-31B-it-GGUF (Port 11434)

    CLaSp (arXiv:2505.24196): E2B serves as the "shallow draft" (half the params),
    E4B as the full verifier. Expected 1.5-2.5x iGPU throughput improvement when
    draft acceptance rate is ≥50%. Harness invariant N2 preserved (NPU = llama3.2-1b-FLM).
    """

    # 1. NPU Tier - Fast routing/classification pass
    # llama3.2-1b-FLM chosen over qwen3.5-4b-FLM: fits in XDNA2 on-chip SRAM (42 TPS vs 8.6 TPS)
    npu_tier = build_gaia_native_tier(
        model_id="llama3.2-1b-FLM", base_url=f"http://localhost:{npu_port}/v1", silent=True
    )

    # 2. iGPU Tier - Deep context analysis (Wave32 unlocked)
    # With CLaSp speculative drafting when draft_port is configured
    if clasp_draft_port is not None:
        try:
            from cohezion.inference.clasp_tier import build_clasp_igpu_tier

            igpu_tier = build_clasp_igpu_tier(
                draft_port=clasp_draft_port,
                verify_port=igpu_port,
                draft_model="Gemma-4-E2B-it-GGUF",
                verify_model="Gemma-4-E4B-it-GGUF",
                silent=True,
            )
            logger.info(
                "CLaSp iGPU tier enabled: E2B draft (port %d) → E4B verify (port %d)",
                clasp_draft_port,
                igpu_port,
            )
        except ImportError:
            logger.warning("CLaSp tier unavailable, falling back to standard E4B iGPU")
            igpu_tier = build_gaia_native_tier(
                model_id="Gemma-4-E4B-it-GGUF",
                base_url=f"http://localhost:{igpu_port}/v1",
                silent=True,
            )
    else:
        igpu_tier = build_gaia_native_tier(
            model_id="Gemma-4-E4B-it-GGUF", base_url=f"http://localhost:{igpu_port}/v1", silent=True
        )

    # 3. CPU Tier - Ultimate fallback reasoning (AVX-512)
    cpu_tier = build_gaia_native_tier(
        model_id="Gemma-4-31B-it-GGUF", base_url=f"http://localhost:{cpu_port}/v1", silent=True
    )

    return TieredOrchestrator(
        tiers=[
            (npu_tier, QualityGate(min_chars=500)),  # NPU must provide a solid start
            (igpu_tier, QualityGate(min_chars=750)),  # iGPU gate calibrated (EXP-ROUTE-12)
            (cpu_tier, QualityGate.TRUST),  # CPU for guaranteed completion
        ],
        pre_dispatch_classifier=classify_task,  # overrides quality gate per output_type
    )
