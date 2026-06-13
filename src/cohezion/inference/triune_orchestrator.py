"""
Triune Orchestrator: Automated hardware-aware routing for GAIA experiments.
Seamlessly routes complex tasks across NPU, iGPU, and CPU on AMD Strix Halo.
"""

from __future__ import annotations

import logging
from typing import Any

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


# F3 (adversarial audit 2026-06-09): run_batch reads orchestrator._max_concurrent; left
# unset it ran an UNBOUNDED asyncio.gather against the single :13305 (the saturation that
# starved the live bot, item 113). Cap concurrent in-flight requests for fleet fairness.
_TRIUNE_MAX_CONCURRENT = 4

# Cloud escalation ladder — cheapest-first. Local silicon (tiers 0-2) is tried first and
# always dominates on amplitude; these cloud rungs are reached ONLY when a local quality
# gate fails. Defined once so both build sites (RAM-low cloud-only path + the main path)
# share one source of truth and the ladder is tunable in one place.
# Token asymmetry (per 1M tok, in/out): Haiku $0.80/$4 · Sonnet $3/$15 · Opus $15/$75.
_CLOUD_LADDER_BASE: tuple[str, ...] = ("claude-haiku-4-5", "claude-sonnet-4-6")

# Premium rungs — reserved for genuinely difficult tasks, OFF by default
# (include_premium=False): auto-escalating to these top-tier models is a cost-increasing,
# default-on behaviour change which the 2026-06-09 audit (STRAT) warns against shipping
# unmeasured. Flip on per call once the usage monitor (scripts/usage_monitor.py) shows
# budget headroom. Order is capability-ascending (escalate to the more capable model on a
# gate failure): Opus → Fable. Reached only after Sonnet fails, so Fable is intrinsically
# "sparing" — only the very hardest tasks ever reach it.
#   claude-opus-4-8: $15/$75 per 1M (in/out).
#   claude-fable-5:  $10/$50 per 1M — GA 2026-06-09, Anthropic's most capable GA model
#     (above the Opus class). Note: cheaper PER TOKEN than Opus but kept as the final rung
#     per the operator's "escalate to Opus, THEN Fable (sparingly)" intent. (Mythos 5 is the
#     same model with safeguards lifted — NOT generally available, Project Glasswing only —
#     so it is intentionally NOT wired.)
_CLOUD_LADDER_PREMIUM: tuple[str, ...] = ("claude-opus-4-8", "claude-fable-5")

# Extension slot for any future rung above Fable. Empty — Fable (the prior "unknown") is now
# resolved and lives in the premium tuple above.
_CLOUD_LADDER_EXTENSION: tuple[str, ...] = ()

# ── Cohezion Omni model presets ──────────────────────────────────────────────
# Custom omni models registered via `recipe: collection.omni` in Lemonade's
# user_models.json. Each bundles a planner LLM (tool-calling label) with image,
# TTS, and ASR components — enabling unified multimodal dispatches through :13305.
# See plan Task G in ~/.claude/plans/i-mispoke-the-extraneous-radiant-dongarra.md.
OMNI_LITE_MODEL_ID = "Cohezion-Omni-Lite"  # Gemma-4-E4B + SD-Turbo (~8 GB)
OMNI_DENSE_MODEL_ID = "Cohezion-Omni-Dense"  # Qwen3.6-35B + Flux-2-Klein (~40+ GB)
_OMNI_DENSE_RAM_GB = 36.0  # Dense planner: ~20 GB weights + KV overhead
_OMNI_LITE_RAM_GB = 12.0  # Lite planner:  ~4 GB weights  + KV overhead


class OmniRequest:
    """Multimodal request: text prompt + per-call image model override."""

    def __init__(self, prompt: str, image_model: str = "SD-Turbo") -> None:
        self.prompt = prompt
        self.image_model = image_model


class OmniTier:
    """Local multimodal tier: planner LLM + image generation via :13305 router.

    Satisfies the ``Runnable`` protocol — accepts both a plain string (called by
    ``TieredOrchestrator``) and an ``OmniRequest`` (called by ``OmniRunnable``).
    N3 guard is the router's responsibility; this tier NEVER triggers model loads.
    """

    def __init__(self, planner_model: str, image_model: str, model_id: str) -> None:
        self._planner_model = planner_model
        self._image_model = image_model
        self.model_id = model_id

    async def run(self, prompt_or_req: Any, **kwargs: Any) -> Any:
        from cohezion.inference.orchestrator import OrchestrationResult

        prompt = (
            prompt_or_req.prompt if isinstance(prompt_or_req, OmniRequest) else str(prompt_or_req)
        )
        # Forward to :13305 omni recipe (collection.omni); fail-soft stub for now —
        # full multimodal dispatch wired after custom model registration (plan Task G).
        return OrchestrationResult(
            text=prompt,
            primary_model=self.model_id,
            final_model=self.model_id,
            escalation_count=0,
        )


def build_omni_lite_tier() -> OmniTier:
    """Cohezion-Omni-Lite: Gemma-4-E4B planner + SD-Turbo image (~8 GB RAM)."""
    return OmniTier(
        planner_model="Gemma-4-E4B-it-GGUF",
        image_model="SD-Turbo",
        model_id=OMNI_LITE_MODEL_ID,
    )


def build_omni_dense_tier() -> OmniTier:
    """Cohezion-Omni-Dense: Qwen3.6-35B planner + Flux-2-Klein image (~40+ GB RAM)."""
    return OmniTier(
        planner_model="Qwen3.6-35B-A3B-MTP-GGUF",
        image_model="Flux-2-Klein-9B-GGUF",
        model_id=OMNI_DENSE_MODEL_ID,
    )


def build_omni_tier() -> OmniTier:
    """Backwards-compatible alias → Dense preset (original OMNI_MODEL_ID intent)."""
    return build_omni_dense_tier()


class OmniRunnable:
    """Async runner: wraps an OmniTier and dispatches OmniRequest objects.

    ``_tier`` can be replaced after construction (test injection pattern):
        runnable._tier = fake_tier
    """

    def __init__(self, image_model: str = "SD-Turbo") -> None:
        self._image_model = image_model
        self._tier: Any = build_omni_lite_tier()

    async def run(self, prompt: str) -> Any:
        req = OmniRequest(prompt=prompt, image_model=self._image_model)
        return await self._tier.run(req)


def _cloud_ladder(include_premium: bool = False) -> list[tuple]:
    """Cloud escalation tiers as ``(model, QualityGate.TRUST)`` tuples, cheapest-first.

    Default = Haiku → Sonnet. ``include_premium=True`` appends Opus as a final, priciest
    rung. The inert extension slot ("Fable") is always appended last but is empty until a
    real model id is resolved.
    """
    models = list(_CLOUD_LADDER_BASE)
    if include_premium:
        models += list(_CLOUD_LADDER_PREMIUM)
    models += list(_CLOUD_LADDER_EXTENSION)
    return [(m, QualityGate.TRUST) for m in models]  # type: ignore[list-item]


def build_triune_orchestrator(
    *,
    npu_port: int = 13306,  # allow-direct-port: API-stability param — body uses router post-Phase2; CLaSp igpu_port uses direct
    igpu_port: int = 13307,  # allow-direct-port: CLaSp verify_port — direct iGPU connection required for speculative decoding
    cpu_port: int = 13309,  # allow-direct-port: N2 harness invariant — preserved per harness.md N2
    router_cpu_port: int = 13305,
    clasp_draft_port: int
    | None = 13308,  # allow-direct-port: CLaSp speculative decoding — dual-port by design
    include_cloud: bool = True,
    include_premium: bool = False,
    include_omni: bool = False,
) -> TieredOrchestrator:
    """
    Constructs a TieredOrchestrator mapped to the Triune Substrate.

    Tiers (rich tapestry, router-centric post-Phase 2):
    0. NPU (FastFlowLM): llama3.2-1b-FLM → router :13305 (was :13306 pre-Phase2)  # allow-direct-port: docstring topology reference
    1. iGPU (CLaSp/TurboKV Wave32): Gemma-4-E4B-it-GGUF → router :13305  # allow-direct-port: docstring topology reference; CLaSp uses :13307/:13308 directly
       With CLaSp: draft via Gemma-4-E2B-it-GGUF (:13308) + verify (:13307) — speculative decode only  # allow-direct-port: CLaSp retained dual-port
    2. CPU (Vectorized AVX-512): Gemma-4-31B-it-GGUF → router :13305 (direct :13309 fallback)  # allow-direct-port: docstring topology reference
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
                tiers_cloud_only = _cloud_ladder(include_premium)
            if not tiers_cloud_only:
                logger.warning(
                    "OOM guard: include_cloud=False and RAM low — proceeding with local (risk accepted)."
                )
            else:
                orch_cloud = TieredOrchestrator(tiers=tiers_cloud_only)
                orch_cloud._max_concurrent = _TRIUNE_MAX_CONCURRENT  # F3: fleet-fairness cap
                return orch_cloud
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
        build_router_cpu_tier,
        build_router_igpu_tier,
        build_router_npu_tier,
    )

    # NPU Tier — router-centric (Phase 2): targets :13305 unified router.
    # npu_port param retained in signature for API stability; not used in body post-Phase2.
    npu_tier = build_router_npu_tier(model_id="llama3.2-1b-FLM")

    # 2. iGPU Tier — deep context analysis, Wave32 ROCWMMA
    # CLaSp speculative drafting only when BOTH draft and verify ports are live.
    # If either port is offline, fall back to router iGPU tier.
    # iGPU FLM model: deepseek-r1-0528-8b-FLM (harness N1/N2 spec).
    # CLaSp speculative decoding: port 13308 (E2B draft) + port 13307 (E4B verify) — retained dual-port.  # allow-direct-port: CLaSp topology documentation
    # When CLaSp draft port is offline (default), router iGPU tier is used.
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
            logger.warning("CLaSp tier unavailable (%s), falling back to router iGPU tier", exc)
            igpu_tier = build_router_igpu_tier(model_id="deepseek-r1-0528-8b-FLM")
    else:
        if not _igpu_live:
            logger.debug("iGPU port %d offline — using router iGPU tier as fallback", igpu_port)
        # iGPU non-CLaSp path: router-centric (Phase 2), targets :13305 unified router.
        igpu_tier = build_router_igpu_tier(model_id="deepseek-r1-0528-8b-FLM")

    # 3. CPU Tier — Gemma-4-31B reasoner ($0). The dedicated direct :13309 server is the default
    # alternative (N2); when it is unreachable, fall back to the router (:13305) with
    # llamacpp_backend=cpu — the canonical unified interface that serves the catalog on demand
    # (router-centric topology: the dedicated per-port servers are frequently down). This mirrors
    # the iGPU CLaSp-vs-direct selection above: pick the live path at build time.
    #
    # OOM gate (N3, mirrors the guard at the top of this fn): the 31B reasoner needs a bounded
    # ctx_size (≤16384) AND enough free RAM. We require the same 16 GB MemorySnapshot buffer used
    # above plus the reasoner's own footprint. If RAM is unsafe we OMIT the CPU tier entirely so
    # escalation falls through to the cloud reasoner rather than risk an OOM hang (N3 incident).
    _CPU_REASONER_SIZE_GB = 20.0  # Gemma-4-31B ~Q4 weights; bounded-ctx KV adds little
    _cpu_ram_safe = True
    try:
        from cohezion.competition.orchestrator.resource_guard import MemorySnapshot

        _snap = MemorySnapshot.capture()
        _cpu_ram_safe = _snap.available_gb >= (16.0 + _CPU_REASONER_SIZE_GB)
    except Exception as _rg_err:  # fail-soft: don't block tier build on a probe error
        logger.debug("CPU RAM gate check failed (non-blocking): %s", _rg_err)

    cpu_tier = None
    if _cpu_ram_safe:
        if _check_port(cpu_port):
            cpu_tier = build_direct_cpu_tier(port=cpu_port, model_id="Gemma-4-31B-it-GGUF")
            logger.info("CPU reasoner tier: direct :%d (Gemma-4-31B)", cpu_port)
        else:
            cpu_tier = build_router_cpu_tier(port=router_cpu_port, model_id="Gemma-4-31B-it-GGUF")
            logger.info(
                "CPU reasoner tier: direct :%d down → router :%d (llamacpp_backend=cpu, "
                "bounded ctx)",
                cpu_port,
                router_cpu_port,
            )
    else:
        logger.warning(
            "OOM guard: CPU reasoner (Gemma-4-31B, ~%.0f GB) omitted — RAM unsafe. "
            "Reasoning tasks escalate to cloud.",
            _CPU_REASONER_SIZE_GB,
        )

    # Quality gates for DirectLemonadeTier (direct HTTP inference).
    # Note: pre_dispatch_classifier overrides tier-0 and tier-1 gates based on output_type.
    # These static values are the fallback when the classifier is not set.
    tiers: list[tuple] = [
        (npu_tier, QualityGate(min_chars=1)),  # NPU: XDNA2 SRAM, 40 TPS, $0
        (igpu_tier, QualityGate(min_chars=5)),  # iGPU: ROCWMMA, $0
    ]
    if cpu_tier is not None:
        tiers.append((cpu_tier, QualityGate(min_chars=10)))  # CPU reasoner: AVX-512, $0

    # 4. Omni tier — Lite or Dense, selected by available RAM (opt-in via include_omni).
    # N3 guard: this tier NEVER loads models — it dispatches to :13305 which has already
    # bounded ctx_size for all heavy models (recipe_options.ctx_size=16384, 2026-06-09 fix).
    if include_omni:
        _omni_available_gb = 0.0
        try:
            from cohezion.competition.orchestrator.resource_guard import MemorySnapshot as _OmniMS

            _omni_available_gb = _OmniMS.capture().available_gb
        except Exception as _omni_err:
            logger.debug("Omni RAM probe failed (non-blocking): %s", _omni_err)
        if _omni_available_gb >= _OMNI_DENSE_RAM_GB:
            _omni_tier = build_omni_dense_tier()
            tiers.append((_omni_tier, QualityGate(min_chars=5)))
            logger.info(
                "Omni tier: Dense (%s, %.0f GB available)", OMNI_DENSE_MODEL_ID, _omni_available_gb
            )
        elif _omni_available_gb >= _OMNI_LITE_RAM_GB:
            _omni_tier = build_omni_lite_tier()
            tiers.append((_omni_tier, QualityGate(min_chars=5)))
            logger.info(
                "Omni tier: Lite (%s, %.0f GB available)", OMNI_LITE_MODEL_ID, _omni_available_gb
            )
        else:
            logger.info(
                "Omni tier omitted: insufficient RAM (%.0f GB < %.0f GB min)",
                _omni_available_gb,
                _OMNI_LITE_RAM_GB,
            )

    if include_cloud:
        # Cloud escalation ladder (cheapest-first): Haiku → Sonnet, + Opus when premium is on.
        cloud_tiers = _cloud_ladder(include_premium)
        tiers.extend(cloud_tiers)
        ladder = "→".join(m for m, _ in cloud_tiers)
        logger.info(
            "Triune: %d-tier tapestry (NPU→iGPU→[CPU]→%s), include_cloud=True, premium=%s",
            len(tiers),
            ladder,
            include_premium,
        )
    else:
        logger.info("Triune: %d-tier local-only (NPU→iGPU→[CPU]), include_cloud=False", len(tiers))

    router = PrefillActivationRouter(base_classifier=classify_task)
    orch = TieredOrchestrator(
        tiers=tiers,
        pre_dispatch_classifier=router,  # overrides quality gate per output_type
    )
    orch._max_concurrent = (
        _TRIUNE_MAX_CONCURRENT  # F3: bound run_batch on the single :13305 (item 113)
    )
    return orch
