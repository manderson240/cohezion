"""Inference model DataProducts for Cohezion's Data Mesh.

Each compound-loop inference model is a first-class DataProduct with:
- Schema sourced live from Lemonade OmniRouter API (:13305) — no fabrication
- SLA parameters from harness.md N1 (measured TPS on Strix Halo XDNA2)
- Capability alignment from model labels (HuggingFace model cards via Lemonade)

This wires the inference layer into the event-driven datamesh so:
- DegradationDetector alerts flow as DATA_PRODUCT_QUALITY_ALERT events
- TaskClassifier can resolve preferred_model dynamically from the registry
- DataMeshEventBridge persists product lifecycle events to SurrealDB
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from cohezion.core.event_bus import EventType
from cohezion.data_mesh.data_product import (
    DataProduct,
    DataProductSchema,
    DataProductStatus,
    DataQualityTier,
)
from cohezion.governance.autonomy_engine import AutonomyTier


_OMNI_ROUTER = "http://localhost:13305"
_FETCH_TIMEOUT_S = 2.0

# The 4 models the compound loop uses: SkillRefiner (x2) + SemanticCache + routing
COMPOUND_LOOP_MODELS: list[str] = [
    "llama3.2-1b-FLM",  # NPU: routing/classification, 42 TPS (harness N1)
    "Bonsai-8B-gguf",  # llamacpp: SkillRefiner fast tier
    "nomic-embed-text-v2-moe-GGUF",  # llamacpp: SemanticCache 768D embeddings, 6ms (CA1)
    "deepseek-r1-0528-8b-FLM",  # FLM NPU: SkillRefiner reasoning tier, 10.6 TPS (N1)
]

# SLA: latency targets and quality tiers (source: harness.md N1, measured 2026-06-22)
_SLA: dict[str, dict[str, Any]] = {
    "llama3.2-1b-FLM": {
        "max_latency_ms": 100,
        "quality_tier": DataQualityTier.GOLD,
        "availability_target": 0.99,
    },
    "Bonsai-8B-gguf": {
        "max_latency_ms": 5000,
        "quality_tier": DataQualityTier.SILVER,
        "availability_target": 0.95,
    },
    "nomic-embed-text-v2-moe-GGUF": {
        "max_latency_ms": 50,
        "quality_tier": DataQualityTier.GOLD,
        "availability_target": 0.99,
    },
    "deepseek-r1-0528-8b-FLM": {
        "max_latency_ms": 30000,
        "quality_tier": DataQualityTier.SILVER,
        "availability_target": 0.95,
    },
}

# Use cases from model cards (aligned with label tags Lemonade exposes)
_USE_CASES: dict[str, list[str]] = {
    "llama3.2-1b-FLM": ["classification", "routing", "short_answer"],
    "Bonsai-8B-gguf": ["tool_calling", "skill_refinement", "generation"],
    "nomic-embed-text-v2-moe-GGUF": ["semantic_embedding", "similarity_search", "cache_lookup"],
    "deepseek-r1-0528-8b-FLM": ["reasoning", "analysis", "multi_step"],
}


def _fetch_lemonade_metadata(model_name: str) -> dict[str, Any] | None:
    """Fetch live model metadata from OmniRouter. Returns None if unreachable."""
    try:
        resp = httpx.get(f"{_OMNI_ROUTER}/v1/models/{model_name}", timeout=_FETCH_TIMEOUT_S)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


_SURREAL = "http://localhost:8001/sql"


def _fetch_gauntlet_perf() -> dict[str, dict[str, float]]:
    """Live measured quality/TPS per model from the NPU gauntlet stream.

    Same source the FleetRoster adaptive hook reads (SurrealDB
    ``model_performance``, fed 24/7 by cohezion.inference.npu_gauntlet).
    Returns {} on any error — static harness-N1 SLAs then stand as fallback
    (gauntlet→datamesh wire, 2026-07-17 compound operating doctrine).
    """
    try:
        resp = httpx.post(
            _SURREAL,
            content=(
                "SELECT model, math::mean(quality_score) AS q, math::mean(tps) AS t "
                "FROM model_performance GROUP BY model;"
            ),
            headers={
                "surreal-ns": "cohezion",
                "surreal-db": "main",
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "Authorization": "Basic cm9vdDpyb290",
            },
            timeout=_FETCH_TIMEOUT_S,
        )
        rows = resp.json()[-1].get("result", []) or []
        return {
            r["model"]: {"quality": float(r["q"]), "tps": float(r["t"])}
            for r in rows
            if r.get("q") is not None and r.get("t") is not None
        }
    except Exception:
        return {}


def _tier_from_measured_quality(quality: float) -> DataQualityTier:
    """Map a gauntlet-measured mean quality (0..1 exact-verified) to a tier."""
    if quality >= 0.9:
        return DataQualityTier.GOLD
    if quality >= 0.7:
        return DataQualityTier.SILVER
    return DataQualityTier.BRONZE


def _build_product(
    model_name: str,
    meta: dict[str, Any] | None,
    live_perf: dict[str, float] | None = None,
) -> DataProduct:
    """Build a DataProduct for one inference model.

    All schema field values come from the Lemonade API. If meta is None
    (Lemonade offline at registration), fields are marked 'unverified' and
    the product is created in DRAFT status — no fabrication of unknown values.
    N3 compliance: ctx_size=0 is never used; defaults to min(16384, max_ctx).

    ``live_perf`` ({"quality": .., "tps": ..}) is the gauntlet's MEASURED
    stream for this model; when present it overrides the static harness-N1
    quality tier and is advertised in the schema. Static values are
    fallback-only (doctrine invariant: advertised SLA must track the newest
    measurement).
    """
    sla = _SLA[model_name]
    use_cases = _USE_CASES[model_name]
    verified = meta is not None

    if verified:
        checkpoint: str = meta.get("checkpoint", "unknown")  # type: ignore[assignment]
        labels: list[str] = meta.get("labels", [])
        max_ctx: Any = meta.get("max_context_window", "unknown")
        recipe: str = meta.get("recipe", "unknown")  # type: ignore[assignment]
        raw_ctx = (meta.get("recipe_options") or {}).get("ctx_size")
        # N3: never allow ctx_size=0 — fall back to bounded default
        ctx_size: Any = (
            raw_ctx
            if (raw_ctx and raw_ctx > 0)
            else (min(16384, max_ctx) if isinstance(max_ctx, int) else 16384)
        )
        size_gb: Any = meta.get("size", "unknown")
    else:
        checkpoint = labels = max_ctx = recipe = ctx_size = size_gb = "unverified"  # type: ignore[assignment]
        labels = []

    capabilities = sorted(set(labels) | set(use_cases))

    fields = {
        "checkpoint": f"str — artifact ref: {checkpoint}",
        "recipe": f"str — Lemonade backend: {recipe}",
        "ctx_size": f"int — configured context window: {ctx_size}",
        "max_context_window": f"int — maximum supported: {max_ctx}",
        "capabilities": f"list[str] — {capabilities}",
        "size_gb": f"float — disk size in GB: {size_gb}",
        "use_cases": f"list[str] — {use_cases}",
    }
    quality_tier = sla["quality_tier"]
    if live_perf:
        # Gauntlet-measured values override static harness numbers (live SLA).
        fields["measured_quality"] = (
            f"float — gauntlet mean exact-verified quality: {live_perf['quality']:.3f}"
        )
        fields["measured_tps"] = f"float — gauntlet mean TPS: {live_perf['tps']:.1f}"
        quality_tier = _tier_from_measured_quality(live_perf["quality"])

    schema = DataProductSchema(
        fields=fields,
        version="1.0.0" if verified else "0.0.0",
    )

    return DataProduct(
        product_id=f"inference.{model_name.lower().replace('_', '-').replace('.', '-').replace(':', '-')}",
        name=model_name,
        description=(
            f"{model_name} (checkpoint: {checkpoint}). "
            f"Recipe: {recipe}, ctx_size: {ctx_size}. "
            f"Use cases: {', '.join(use_cases)}. "
            f"[{'schema verified from Lemonade API' if verified else 'schema unverified — Lemonade offline at registration'}]"
        ),
        owner_domain="inference",
        schema=schema,
        output_format="binary" if "embeddings" in labels else "json",
        quality_tier=quality_tier,
        status=DataProductStatus.ACTIVE if verified else DataProductStatus.DRAFT,
        required_autonomy=AutonomyTier.SO3_4,
        max_latency_ms=sla["max_latency_ms"],
        availability_target=sla["availability_target"],
    )


def build_inference_products() -> dict[str, DataProduct]:
    """Build DataProducts for all compound-loop inference models.

    Queries the Lemonade OmniRouter API for each model's live metadata.
    Unverified products (Lemonade offline) are marked DRAFT with schema
    version '0.0.0' rather than silently using fabricated values.

    Returns dict keyed by Lemonade model_name.
    """
    live = _fetch_gauntlet_perf()  # one query for all models; {} on DB error
    return {
        model_name: _build_product(
            model_name, _fetch_lemonade_metadata(model_name), live.get(model_name)
        )
        for model_name in COMPOUND_LOOP_MODELS
    }


# Module-level lazy registry — built from Lemonade API on first access
_registry: dict[str, DataProduct] | None = None


def get_inference_registry() -> dict[str, DataProduct]:
    """Return the inference product registry, building from Lemonade API on first access."""
    global _registry
    if _registry is None:
        _registry = build_inference_products()
    return _registry


def get_product_for_capability(capability: str) -> DataProduct | None:
    """Return the first active DataProduct that supports the given use case.

    Used by TaskClassifier to dynamically resolve preferred_model from the
    registry instead of static _MODEL_HINTS. Checks the USE_CASES alignment
    rather than schema field string parsing.
    """
    registry = get_inference_registry()
    for model_name, use_cases in _USE_CASES.items():
        if capability in use_cases:
            product = registry.get(model_name)
            if product and product.status == DataProductStatus.ACTIVE:
                return product
    return None


async def register_with_event_bus(bus: Any) -> None:
    """Publish DATA_PRODUCT_CREATED events for each compound-loop inference model.

    Called at application startup to wire inference models into the event-driven
    datamesh. DataMeshEventBridge subscribes to these and persists to SurrealDB.
    """
    from cohezion.core.event_bus import Event

    for product in get_inference_registry().values():
        await bus.publish(
            Event(
                type=EventType.DATA_PRODUCT_CREATED,
                source="inference",
                payload={
                    "product_id": product.product_id,
                    "name": product.name,
                    "status": product.status,
                    "quality_tier": product.quality_tier,
                    "max_latency_ms": product.max_latency_ms,
                    "schema_version": product.schema.version,
                },
            )
        )


def emit_quality_alert(product: DataProduct, bus: Any, reason: str = "") -> None:
    """Emit DATA_PRODUCT_QUALITY_ALERT for a degraded inference model.

    Called by DegradationDetector when a model's health score drops below
    threshold. Records the error in the product's observability counters.
    The event flows through DataMeshEventBridge into SurrealDB for audit trail.
    """
    product.record_access(success=False)

    from cohezion.core.event_bus import Event

    event = Event(
        type=EventType.DATA_PRODUCT_QUALITY_ALERT,
        source="inference",
        payload={
            "product_id": product.product_id,
            "name": product.name,
            "domain": product.owner_domain,
            "error_rate": product.error_rate,
            "meets_sla": product.meets_sla,
            "reason": reason,
        },
    )
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(bus.publish(event))
    except RuntimeError:
        asyncio.run(bus.publish(event))
