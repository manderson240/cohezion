"""
Triune Orchestrator: Automated hardware-aware routing for GAIA experiments.
Seamlessly routes complex tasks across NPU, iGPU, and CPU on AMD Strix Halo.

Routing strategy (updated 2026-06-07)
--------------------------------------
All local inference now goes through the **unified Lemonade router on :13305**
(``LemonadeRouterClient`` / ``RouterLemonadeTier``).  The router holds the
model catalog and dispatches by name to the correct physical device (NPU/iGPU/CPU).
Per-device ports 13306 / 13307 / 13309 are deprecated; they are ONLY used as a
direct fallback when :13305 is unreachable.  Do not start new lemond instances on
those ports — the router-centric topology eliminates duplicate model processes and
simplifies memory management.
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

# ---------------------------------------------------------------------------
# Router-aware discovery helpers
# ---------------------------------------------------------------------------

# Canonical model names for each logical tier — matched against the router catalog.
_NPU_MODELS = ("llama3.2-1b-FLM",)
_IGPU_MODELS = ("Granite-4.1-8B-GGUF", "deepseek-r1-0528-8b-FLM", "Gemma-4-E4B-it-GGUF")
_CPU_MODELS = ("Gemma-4-31B-it-GGUF", "Qwen3-0.6B-GGUF")


def _check_port(port: int, timeout: float = 1.0) -> bool:
    """Return True if lemonade is serving on the given port (fast /v1/models check).

    Kept for CLaSp fallback path; prefer ``LemonadeRouterClient.available()``
    for new callers that don't need per-device port probing.
    """
    try:
        import urllib.request

        urllib.request.urlopen(f"http://localhost:{port}/v1/models", timeout=timeout)
        return True
    except Exception:
        return False


def _find_tier_model(hot_names: set[str], candidates: tuple[str, ...]) -> str | None:
    """Return the first candidate that is currently hot on the router, else None."""
    for name in candidates:
        if name in hot_names:
            return name
    return None


def build_triune_orchestrator(
    *,
    router_port: int = 13305,
    # Legacy per-device ports — only used when router_port is unreachable.
    npu_port: int = 13306,
    igpu_port: int = 13307,
    cpu_port: int = 13309,
    clasp_draft_port: int | None = None,  # CLaSp disabled by default (router handles dispatch)
    include_cloud: bool = True,
) -> TieredOrchestrator:
    """
    Constructs a TieredOrchestrator mapped to the Triune Substrate.

    Routing strategy (2026-06-07)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Tier construction now probes the **unified Lemonade router on :13305** first.
    When the router is available, ``RouterLemonadeTier`` instances are built for
    whichever NPU/iGPU/CPU models are hot — no per-device port management needed.
    Per-device ports (13306/13307/13309) are the FALLBACK path only.

    Tiers:
    0. NPU  (llama3.2-1b-FLM)     — XDNA2 SRAM, ~42 TPS, $0
    1. iGPU (Granite-4.1-8B-GGUF) — Vulkan/GPU, $0
    2. CPU  (Gemma-4-31B-it-GGUF) — AVX-512, $0
    3. Haiku 4.5 (cloud)           — 3.75× cheaper than Sonnet, covers CPU gate failures
    4. Sonnet 4.6 (cloud)          — final fallback for BBQ low-and-slow synthesis

    Token asymmetry: Tiers 0-2 cost $0.00. Tier 3 ≈ $0.001/call. Tier 4 ≈ $0.01/call.
    """

    # OOM guard: check available RAM before loading any local model tiers.
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
        raise
    except Exception as _oom_err:
        logger.debug("OOM guard check failed (non-blocking): %s", _oom_err)

    # -------------------------------------------------------------------------
    # PATH A — Router-centric (preferred): build tiers via :13305 by model name.
    # -------------------------------------------------------------------------
    from cohezion.compound.fleet_client import LemonadeRouterClient, RouterLemonadeTier

    _router = LemonadeRouterClient(port=router_port)
    if _router.available():
        hot_names = {m.model_name for m in _router.hot_models()}
        logger.info("Triune: router :%d available — hot models: %s", router_port, sorted(hot_names))

        npu_model = _find_tier_model(hot_names, _NPU_MODELS)
        igpu_model = _find_tier_model(hot_names, _IGPU_MODELS)
        cpu_model = _find_tier_model(hot_names, _CPU_MODELS)

        local_tiers: list[tuple] = []
        if npu_model:
            local_tiers.append(
                (RouterLemonadeTier(_router, npu_model, max_tokens=256), QualityGate(min_chars=1))
            )
            logger.debug("Triune: NPU tier → %s via router :%d", npu_model, router_port)
        else:
            logger.debug(
                "Triune: no NPU model hot on router :%d (candidates %s)", router_port, _NPU_MODELS
            )

        if igpu_model:
            local_tiers.append(
                (RouterLemonadeTier(_router, igpu_model, max_tokens=512), QualityGate(min_chars=5))
            )
            logger.debug("Triune: iGPU tier → %s via router :%d", igpu_model, router_port)
        else:
            logger.debug(
                "Triune: no iGPU model hot on router :%d (candidates %s)", router_port, _IGPU_MODELS
            )

        if cpu_model:
            local_tiers.append(
                (RouterLemonadeTier(_router, cpu_model, max_tokens=512), QualityGate(min_chars=10))
            )
            logger.debug("Triune: CPU tier → %s via router :%d", cpu_model, router_port)
        else:
            logger.debug(
                "Triune: no CPU model hot on router :%d (candidates %s)", router_port, _CPU_MODELS
            )

        tiers: list[tuple] = local_tiers

    else:
        # -------------------------------------------------------------------------
        # PATH B — Legacy fallback: direct per-device ports (13306/13307/13309).
        # Used only when router is unreachable (e.g. lemonade not running).
        # -------------------------------------------------------------------------
        logger.warning(
            "Triune: router :%d unreachable — falling back to direct ports "
            "(NPU:%d iGPU:%d CPU:%d). Start lemonade to use the router.",
            router_port,
            npu_port,
            igpu_port,
            cpu_port,
        )
        from cohezion.inference.direct_tier import (
            build_direct_cpu_tier,
            build_direct_igpu_tier,
            build_direct_npu_tier,
        )

        npu_tier = build_direct_npu_tier(port=npu_port, model_id="llama3.2-1b-FLM")

        # CLaSp speculative drafting: only when BOTH draft and verify ports are live.
        _igpu_live = _check_port(igpu_port)
        _draft_live = clasp_draft_port is not None and _check_port(clasp_draft_port)
        if _igpu_live and _draft_live and clasp_draft_port is not None:
            try:
                from cohezion.inference.clasp_tier import build_clasp_igpu_tier

                igpu_tier = build_clasp_igpu_tier(
                    draft_port=clasp_draft_port,  # type: ignore[arg-type]
                    verify_port=igpu_port,
                    draft_model="Gemma-4-E2B-it-GGUF",
                    verify_model="Gemma-4-E4B-it-GGUF",
                    silent=True,
                )
                logger.info("CLaSp fallback iGPU: E2B:%d → E4B:%d", clasp_draft_port, igpu_port)
            except Exception as exc:
                logger.warning("CLaSp unavailable (%s), using direct iGPU", exc)
                igpu_tier = build_direct_igpu_tier(
                    port=igpu_port, model_id="deepseek-r1-0528-8b-FLM"
                )
        else:
            igpu_tier = build_direct_igpu_tier(port=igpu_port, model_id="deepseek-r1-0528-8b-FLM")

        cpu_tier = build_direct_cpu_tier(port=cpu_port, model_id="Gemma-4-31B-it-GGUF")

        tiers = [
            (npu_tier, QualityGate(min_chars=1)),
            (igpu_tier, QualityGate(min_chars=5)),
            (cpu_tier, QualityGate(min_chars=10)),
        ]

    if include_cloud:
        tiers.append(("claude-haiku-4-5", QualityGate.TRUST))  # type: ignore[arg-type]
        tiers.append(("claude-sonnet-4-6", QualityGate.TRUST))  # type: ignore[arg-type]
        logger.info(
            "Triune: %d local + 2 cloud tiers (→Haiku→Sonnet), include_cloud=True",
            len(tiers) - 2,
        )
    else:
        logger.info("Triune: %d local-only tiers, include_cloud=False", len(tiers))

    dispatch_router = PrefillActivationRouter(base_classifier=classify_task)
    return TieredOrchestrator(
        tiers=tiers,
        pre_dispatch_classifier=dispatch_router,
    )
