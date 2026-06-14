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

# ── Triune substrate collection definitions ────────────────────────────────
# Named Lemonade collections bundling the three local tiers so the router can
# reference them as a unit. Registered via POST :13305/v1/pull.
# Sized to fit in 128 GB unified RAM with ≥30 GB buffer for OS + other ops.
#
#   TruineBase  ≈ 27 GB: NPU (1.3 GB) + iGPU (6 GB) + CPU (20 GB)
#   TruineDense ≈ 32 GB: TruineBase + embed (0.5 GB) + CLaSp draft (4 GB)
#
# ctx_size=16384 on all heavy models (N3 harness invariant).
_TRIUNE_COLLECTIONS: dict[str, dict] = {
    "user.TruineBase": {
        "recipe": "collection.omni",
        "estimated_gb": 27.0,
        "components": [
            {"label": "npu", "model_name": "llama3.2-1b-FLM"},
            {"label": "igpu", "model_name": "Gemma-4-E4B-it-GGUF"},
            {"label": "cpu", "model_name": "Gemma-4-31B-it-GGUF", "ctx_size": 16384},
        ],
    },
    "user.TruineDense": {
        "recipe": "collection.omni",
        "estimated_gb": 32.0,
        "components": [
            {"label": "npu", "model_name": "llama3.2-1b-FLM"},
            {"label": "igpu", "model_name": "Gemma-4-E4B-it-GGUF"},
            {"label": "cpu", "model_name": "Gemma-4-31B-it-GGUF", "ctx_size": 16384},
            {"label": "embed", "model_name": "nomic-embed-text-v2-moe-GGUF"},
            {"label": "clasp_draft", "model_name": "Gemma-4-E2B-it-GGUF"},
        ],
    },
}
_TRIUNE_RAM_BUFFER_GB = 30.0  # minimum free RAM to leave for OS + other workloads


def register_triune_collections(
    router_port: int = 13305,
    collections: dict[str, dict] | None = None,
    available_ram_gb: float = 128.0,
) -> dict[str, bool]:
    """Register named Lemonade model collections for triune routing.

    Sends POST :router_port/v1/pull for each collection that fits within
    available_ram_gb minus the RAM buffer. Returns {collection_name: success}.

    Skips registration when the router is unreachable (non-blocking).
    """
    import json as _json
    import urllib.request

    target_collections = collections if collections is not None else _TRIUNE_COLLECTIONS
    results: dict[str, bool] = {}
    usable_gb = available_ram_gb - _TRIUNE_RAM_BUFFER_GB

    for coll_name, coll_def in target_collections.items():
        estimated_gb = coll_def.get("estimated_gb", 0.0)
        if estimated_gb > usable_gb:
            logger.info(
                "Skipping collection %s: %.0f GB needed > %.0f GB usable",
                coll_name,
                estimated_gb,
                usable_gb,
            )
            results[coll_name] = False
            continue
        payload = {
            "model_name": coll_name,
            "recipe": coll_def["recipe"],
            "components": coll_def["components"],
        }
        try:
            req = urllib.request.Request(
                f"http://localhost:{router_port}/v1/pull",
                data=_json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:  # noqa: S310
                results[coll_name] = resp.status == 200
                logger.info(
                    "Registered collection %s (%.0f GB) → status %d",
                    coll_name,
                    estimated_gb,
                    resp.status,
                )
        except Exception as exc:
            logger.debug("Collection registration skipped for %s: %s", coll_name, exc)
            results[coll_name] = False

    return results


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


# ── GAIA-native hot-model preference lists ────────────────────────────────────
# Order matters: first match in the router's hot catalog wins.
_NPU_MODELS: tuple[str, ...] = ("llama3.2-1b-FLM", "gemma3-4b-FLM")
_IGPU_MODELS: tuple[str, ...] = (
    "Granite-4.1-8B-GGUF",
    "deepseek-r1-0528-8b-FLM",
    "Gemma-4-E4B-it-GGUF",
)
_CPU_MODELS: tuple[str, ...] = ("Gemma-4-31B-it-GGUF", "gemma-4-31b", "qwen3-30b")


def build_gaia_native_tier(
    port: int,
    *,
    device_class: str = "npu",
    fallback_model_id: str = "llama3.2-1b-FLM",
    max_tokens: int = 256,
) -> Any:
    """Build a tier via GAIA-native hot-model discovery on the router.

    Queries the router's hot catalog for the best model matching ``device_class``,
    falling back to ``fallback_model_id`` when discovery fails or no preferred model
    is hot.
    """
    from cohezion.compound.fleet_client import LemonadeRouterClient, RouterLemonadeTier

    router = LemonadeRouterClient(port=port)
    prefer = {"npu": _NPU_MODELS, "gpu": _IGPU_MODELS, "cpu": _CPU_MODELS}.get(device_class, ())
    try:
        hot_by_name = {m.model_name: m for m in router.hot_models() if m.device == device_class}
        for model_name in prefer:
            if model_name in hot_by_name:
                return RouterLemonadeTier(router, model_name, max_tokens=max_tokens)
    except Exception as _err:
        logger.debug("build_gaia_native_tier hot-model discovery failed: %s", _err)
    return RouterLemonadeTier(router, fallback_model_id, max_tokens=max_tokens)


def build_triune_orchestrator(
    *,
    npu_port: int = 13306,  # allow-direct-port: PATH B direct fallback; PATH A uses router_port
    igpu_port: int = 13307,  # allow-direct-port: PATH B direct fallback
    cpu_port: int = 13309,  # allow-direct-port: N2 harness invariant — preserved per harness.md N2
    router_port: int = 13305,
    clasp_draft_port: int
    | None = 13308,  # allow-direct-port: CLaSp speculative decoding — dual-port by design
    include_cloud: bool = False,
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

    # PATH A / PATH B routing: use router-centric GAIA-native discovery when the router is
    # reachable; fall back to direct-port builders when it is not.
    from cohezion.compound.fleet_client import LemonadeRouterClient

    _router_probe = LemonadeRouterClient(port=router_port)
    if _router_probe.available():
        # PATH A — router is live: build all tiers via GAIA-native hot-model discovery.
        logger.debug(
            "PATH A: router :%d reachable — using GAIA-native tier discovery.", router_port
        )
        npu_tier = build_gaia_native_tier(
            router_port, device_class="npu", fallback_model_id="llama3.2-1b-FLM", max_tokens=256
        )
        igpu_tier = build_gaia_native_tier(
            router_port,
            device_class="gpu",
            fallback_model_id="deepseek-r1-0528-8b-FLM",
            max_tokens=512,
        )
        cpu_tier = build_gaia_native_tier(
            router_port, device_class="cpu", fallback_model_id="Gemma-4-31B-it-GGUF", max_tokens=512
        )
    else:
        # PATH B — router unreachable: fall back to direct per-port builders.
        logger.debug(
            "PATH B: router :%d unreachable — using direct-port tier builders.", router_port
        )
        from cohezion.inference.direct_tier import (
            build_direct_cpu_tier,
            build_direct_igpu_tier,
            build_direct_npu_tier,
        )

        npu_tier = build_direct_npu_tier(port=npu_port, model_id="llama3.2-1b-FLM")
        igpu_tier = build_direct_igpu_tier(port=igpu_port, model_id="deepseek-r1-0528-8b-FLM")
        cpu_tier = build_direct_cpu_tier(port=cpu_port, model_id="Gemma-4-31B-it-GGUF")

    tiers: list[tuple] = [
        (npu_tier, QualityGate(min_chars=1)),  # NPU: XDNA2 SRAM, 40 TPS, $0
        (igpu_tier, QualityGate(min_chars=5)),  # iGPU: ROCWMMA, $0
        (cpu_tier, QualityGate(min_chars=10)),  # CPU reasoner: AVX-512, $0
    ]

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
