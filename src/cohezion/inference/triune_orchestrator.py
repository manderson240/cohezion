"""
Triune Orchestrator: Automated hardware-aware routing for GAIA experiments.
Seamlessly routes complex tasks across NPU, iGPU, and CPU on AMD Strix Halo.
"""

from __future__ import annotations

import logging

from cohezion.inference.activation_router import PrefillActivationRouter
from cohezion.inference.orchestrator import (
    QualityGate,
    TieredOrchestrator,
)
from cohezion.inference.task_classifier import classify as classify_task


logger = logging.getLogger(__name__)


def _check_port(port: int, timeout: float = 1.0) -> bool:
    """Return True if lemonade is serving on the given port (fast /v1/models check)."""
    try:
        import urllib.request

        urllib.request.urlopen(f"http://localhost:{port}/v1/models", timeout=timeout)
        return True
    except Exception:
        return False


def build_triune_orchestrator(
    *,
    npu_port: int = 13306,
    igpu_port: int = 13307,
    cpu_port: int = 13309,
    clasp_draft_port: int | None = 13308,
    include_cloud: bool = True,
) -> TieredOrchestrator:
    """
    Constructs a TieredOrchestrator mapped to the Triune Substrate.

    Tiers (rich tapestry):
    0. NPU (FastFlowLM): llama3.2-1b-FLM (Port 13306) — fits in XDNA2 SRAM, 42 TPS, $0
    1. iGPU (CLaSp/TurboKV Wave32): Gemma-4-E4B-it-GGUF (Port 13307), $0
       With CLaSp: draft via Gemma-4-E2B-it-GGUF (Port 13308, optional)
    2. CPU (Vectorized AVX-512): Gemma-4-31B-it-GGUF (Port 13309, lemonade), $0
    3. Haiku 4.5 (cloud): 3.75× cheaper than Sonnet, covers CPU quality gate failures
    4. Sonnet 4.6 (cloud): final fallback for BBQ low-and-slow and complex synthesis

    Token asymmetry: Tiers 0-2 cost $0.00. Tier 3 ≈ $0.001/avg call. Tier 4 ≈ $0.01/avg call.
    Feynman routing: local always dominates on amplitude; cloud only invoked on gate failure.

    CLaSp (arXiv:2505.24196): E2B serves as the "shallow draft" (half the params),
    E4B as the full verifier. Expected 1.5-2.5x iGPU throughput improvement when
    draft acceptance rate is ≥50%. Harness invariant N2 preserved (NPU = llama3.2-1b-FLM).
    """

    # OOM guard: check available RAM before loading any local model tiers.
    # ResourceGuard enforces a 16 GB safety buffer — skips local tiers if unsafe.
    try:
        from cohezion.competition.orchestrator.resource_guard import MemorySnapshot

        snap = MemorySnapshot.capture()
        if snap.available_gb < 16.0:
            logger.warning(
                "OOM guard: only %.1f GB RAM available (need 16 GB buffer). "
                "Local tiers skipped — cloud-only orchestration.",
                snap.available_gb,
            )
            tiers_cloud_only: list[tuple] = []
            if include_cloud:
                tiers_cloud_only.append(("claude-haiku-4-5", QualityGate.TRUST))  # type: ignore[arg-type]
                tiers_cloud_only.append(("claude-sonnet-4-6", QualityGate.TRUST))  # type: ignore[arg-type]
            if not tiers_cloud_only:
                logger.warning(
                    "OOM guard: include_cloud=False and RAM low — proceeding with local (risk accepted)."
                )
            else:
                return TieredOrchestrator(tiers=tiers_cloud_only)
        logger.debug("OOM guard: %.1f GB available — local tiers safe to load.", snap.available_gb)
    except ValueError:
        raise  # Re-raise programming errors (e.g., empty tiers list)
    except Exception as _oom_err:
        logger.debug("OOM guard check failed (non-blocking): %s", _oom_err)

    # 1. NPU Tier — fast routing/classification (XDNA2 SRAM, 40 TPS, $0)
    # Uses DirectLemonadeTier (direct httpx) to bypass GAIA LemonadeManager singleton.
    # GAIA singleton conflict: class-level _initialized means all tiers share one port.
    # Direct HTTP is proven correct (exp_OOOO3/PPPP3, 2026-05-30, round 13).
    from cohezion.inference.direct_tier import (
        build_direct_cpu_tier,
        build_direct_igpu_tier,
        build_direct_npu_tier,
    )

    npu_tier = build_direct_npu_tier(port=npu_port, model_id="llama3.2-1b-FLM")

    # 2. iGPU Tier — deep context analysis, Wave32 ROCWMMA
    # CLaSp speculative drafting only when BOTH draft and verify ports are live.
    # If either port is offline, fall back to direct HTTP iGPU tier immediately.
    # iGPU FLM model: deepseek-r1-0528-8b-FLM on port 13307 (harness N1/N2 spec).
    # CLaSp speculative decoding is only available when port 13308 (E2B draft) is live.
    # When 13308 is offline (default), use direct FLM iGPU tier instead.
    _igpu_live = _check_port(igpu_port)
    _draft_live = clasp_draft_port is not None and _check_port(clasp_draft_port)
    if _igpu_live and _draft_live:
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
        except Exception as exc:
            logger.warning("CLaSp tier unavailable (%s), falling back to direct FLM iGPU", exc)
            igpu_tier = build_direct_igpu_tier(port=igpu_port, model_id="deepseek-r1-0528-8b-FLM")
    else:
        if not _igpu_live:
            logger.debug("iGPU port %d offline — iGPU slot unavailable", igpu_port)
        igpu_tier = build_direct_igpu_tier(port=igpu_port, model_id="deepseek-r1-0528-8b-FLM")

    # 3. CPU Tier — AVX-512 reasoning fallback ($0)
    cpu_tier = build_direct_cpu_tier(port=cpu_port, model_id="Gemma-4-31B-it-GGUF")

    # Quality gates for DirectLemonadeTier (direct HTTP inference).
    # Note: pre_dispatch_classifier overrides tier-0 and tier-1 gates based on output_type.
    # These static values are the fallback when the classifier is not set.
    tiers: list[tuple] = [
        (npu_tier, QualityGate(min_chars=1)),  # NPU: XDNA2 SRAM, 40 TPS, $0
        (igpu_tier, QualityGate(min_chars=5)),  # iGPU: ROCWMMA, $0
        (cpu_tier, QualityGate(min_chars=10)),  # CPU: AVX-512, $0
    ]

    if include_cloud:
        # Haiku 4.5: cloud tier 1 — 3.75× cheaper than Sonnet, covers CPU gate failures
        tiers.append(("claude-haiku-4-5", QualityGate.TRUST))  # type: ignore[arg-type]
        # Sonnet 4.6: cloud tier 2 — final fallback for BBQ low-and-slow synthesis
        tiers.append(("claude-sonnet-4-6", QualityGate.TRUST))  # type: ignore[arg-type]
        logger.info("Triune: 5-tier tapestry (NPU→iGPU→CPU→Haiku→Sonnet), include_cloud=True")
    else:
        logger.info("Triune: 3-tier local-only (NPU→iGPU→CPU), include_cloud=False")

    router = PrefillActivationRouter(base_classifier=classify_task)
    return TieredOrchestrator(
        tiers=tiers,
        pre_dispatch_classifier=router,  # overrides quality gate per output_type
    )
