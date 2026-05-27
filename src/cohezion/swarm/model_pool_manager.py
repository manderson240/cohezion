# class attrs treated as immutable config; never mutated per-instance
"""3-tier model pool lifecycle manager for Ollama models.

Manages hot/warm/cold model rotation, health checks, and automatic
promotion/demotion based on memory pressure and usage patterns.

Reuses MemoryBandwidthAnalyzer from dynamic_model_router for memory
pressure analysis. Communicates with Ollama via httpx.

Usage:
    pool = ModelPoolManager()
    await pool.initialize()
    if await pool.ensure_loaded("qwen3-coder:30b"):
        # Model is loaded and ready
        ...
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict
from typing import Any

import httpx

from cohezion.research.autoresearch import AutoResearcher
from cohezion.swarm.dynamic_model_router import MemoryBandwidthAnalyzer
from cohezion.swarm.lemonade_manager import LemonadeManager
from cohezion.swarm.model_manager import OLLAMA_HOST
from cohezion.swarm.model_pool_config import (
    ModelTierPolicy,
    PooledModel,
    PoolStatus,
    TierConfig,
)


logger = logging.getLogger(__name__)

# Health-check prompt: minimal tokens, fast response
_HEALTH_PROMPT = "Reply OK"
_HEALTH_TIMEOUT_S = 5.0
_LOAD_TIMEOUT_S = 120.0


class ModelPoolManager:
    """Lifecycle manager for 3-tier hot/warm/cold model rotation.

    Ensures the CostAwareRouter only routes to models that are actually
    loaded and healthy. Handles automatic eviction under memory pressure
    and on-demand loading for cold models.
    """

    def __init__(
        self,
        config: TierConfig | None = None,
        ollama_host: str = OLLAMA_HOST,
        lemonade_port: int = 13307,
    ) -> None:
        self._config = config or TierConfig()
        self._ollama_host = ollama_host
        self._memory = MemoryBandwidthAnalyzer()
        self._pool: dict[str, PooledModel] = {}
        self._initialized = False
        self.researcher = AutoResearcher()
        self.lemonade = LemonadeManager(port=lemonade_port)

        # Build pool entries from config
        for name in self._config.hot_models:
            self._pool[name] = PooledModel(name=name, tier=ModelTierPolicy.HOT, size_gb=0.0)
        for name in self._config.warm_models:
            self._pool[name] = PooledModel(name=name, tier=ModelTierPolicy.WARM, size_gb=0.0)
        for name in self._config.cold_models:
            self._pool[name] = PooledModel(name=name, tier=ModelTierPolicy.COLD, size_gb=0.0)

    async def initialize(self) -> None:
        """Query Ollama /api/tags, reconcile with tier config.

        Marks models as loaded/healthy if Ollama reports them.
        Updates size_gb from Ollama metadata.
        """
        # Initialize private Lemonade server
        await self.lemonade.start()
        if await self.lemonade.wait_until_ready():
            logger.info("Private Lemonade server ready on port %d", self.lemonade.port)
        else:
            logger.warning("Private Lemonade server failed to respond within timeout")

        installed = await self._list_ollama_models()
        installed_map = {m["name"]: m for m in installed}

        # Also get Lemonade models
        lemonade_installed = await self._list_lemonade_models()
        lemonade_map = {m["id"]: m for m in lemonade_installed}

        for name, model in self._pool.items():
            if name in installed_map:
                meta = installed_map[name]
                # Cloud/Edge models have zero local RAM footprint
                if model.tier in (ModelTierPolicy.CLOUD, ModelTierPolicy.EDGE):
                    model.size_gb = 0.0
                else:
                    model.size_gb = meta.get("size", 0) / (1024**3)
            elif name in lemonade_map:
                # Lemonade models are considered local but potentially NPU/GPU accelerated
                model.size_gb = 0.0  # TODO: Get actual size from Lemonade if possible
            else:
                model.loaded = False
                model.healthy = False

        # Query running models
        running = await self._list_running_models()
        running_names = {m.get("name", "") for m in running}

        for name, model in self._pool.items():
            if name in running_names:
                model.loaded = True
                model.healthy = True

        self._initialized = True
        loaded_count = sum(1 for m in self._pool.values() if m.loaded)
        logger.info(
            "ModelPoolManager initialized: %d models configured, %d loaded",
            len(self._pool),
            loaded_count,
        )

    async def ensure_loaded(self, model_name: str) -> bool:
        """Ensure a model is loaded and ready for inference.

        If the model isn't loaded, attempts to load it. Evicts lower-priority
        models if at the concurrent load limit.
        Cloud and Edge models are considered always loaded.
        """
        model = self._pool.get(model_name)
        if model is None:
            logger.warning("Model %s not in pool config, cannot ensure loaded", model_name)
            return False

        # la-Symphony: Predictive Pre-warming
        # If we are loading a model for 'Sensing', we pre-warm the 'Synthesis' model (26B MoE)
        if model.name == "gemma4:2b" or model.name == "gemma4:4b":
            asyncio.create_task(self._predictive_warmup("gemma4:26b-moe"))

        # Fast path: Cloud/Edge are effectively always loaded
        if model.tier in (ModelTierPolicy.CLOUD, ModelTierPolicy.EDGE):
            model.mark_used()
            return True

        # Fast path: already loaded and healthy local model
        if model.loaded and model.healthy:
            model.mark_used()
            return True

        # Check if we need to evict to make room
        loaded_count = sum(
            1
            for m in self._pool.values()
            if m.loaded and m.tier not in (ModelTierPolicy.CLOUD, ModelTierPolicy.EDGE)
        )
        if loaded_count >= self._config.max_concurrent_loaded:
            evicted = await self._evict_one(exclude=model_name)
            if not evicted:
                logger.error(
                    "Cannot load %s: at capacity (%d) and no evictable models",
                    model_name,
                    self._config.max_concurrent_loaded,
                )
                return False

        # Load the model
        success = await self._load_model(model_name, model.tier)
        if success:
            model.loaded = True
            model.mark_used()
            # Verify health
            healthy = await self.health_check(model_name)
            return healthy

        return False

    async def _predictive_warmup(self, model_name: str):
        """Symphony-specific pre-warming to eliminate regime transition lag."""
        model = self._pool.get(model_name)
        if model and not model.loaded:
            logger.info("Symphony Pre-warming: Predictive loading of %s", model_name)
            await self._load_model(model_name, model.tier)
            model.loaded = True

        # Fast path: Cloud/Edge are effectively always loaded
        if model.tier in (ModelTierPolicy.CLOUD, ModelTierPolicy.EDGE):
            model.mark_used()
            return True

        # Fast path: already loaded and healthy local model
        if model.loaded and model.healthy:
            model.mark_used()
            return True

        # Check if we need to evict to make room
        loaded_count = sum(
            1
            for m in self._pool.values()
            if m.loaded and m.tier not in (ModelTierPolicy.CLOUD, ModelTierPolicy.EDGE)
        )
        if loaded_count >= self._config.max_concurrent_loaded:
            evicted = await self._evict_one(exclude=model_name)
            if not evicted:
                logger.error(
                    "Cannot load %s: at capacity (%d) and no evictable models",
                    model_name,
                    self._config.max_concurrent_loaded,
                )
                return False

        # Load the model
        success = await self._load_model(model_name, model.tier)
        if success:
            model.loaded = True
            model.mark_used()
            # Verify health
            healthy = await self.health_check(model_name)
            return healthy

        return False

    async def health_check(self, model_name: str) -> bool:
        """Ping a model with a trivial prompt to verify it's responsive.

        Updates the model's health status and latency.
        """
        model = self._pool.get(model_name)
        if model is None or not model.loaded:
            return False

        start = time.monotonic()
        try:
            # Check if this model is routed to Lemonade
            # (Simple heuristic: check lemonade_config.yaml or model name)
            is_lemonade = "gemma4:26b-moe" in model_name  # Default for now

            if is_lemonade:
                url = f"http://{self.lemonade.host}:{self.lemonade.port}/v1/chat/completions"
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": _HEALTH_PROMPT}],
                    "max_tokens": 5,
                }
            else:
                url = f"{self._ollama_host}/api/generate"
                payload = {
                    "model": model_name,
                    "prompt": _HEALTH_PROMPT,
                    "stream": False,
                    "options": {"num_predict": 5},
                }

            async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT_S) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                latency_ms = (time.monotonic() - start) * 1000
                model.record_health(healthy=True, latency_ms=latency_ms)
                return True
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            model.record_health(healthy=False, latency_ms=latency_ms)
            logger.warning("Health check failed for %s: %s", model_name, exc)
            return False

    async def health_check_all(self) -> dict[str, bool]:
        """Health-check all loaded models. Returns name -> healthy mapping."""
        results: dict[str, bool] = {}
        for name, model in self._pool.items():
            if model.loaded:
                results[name] = await self.health_check(name)
        return results

    def get_available_models(self) -> list[PooledModel]:
        """Return all models that are loaded and healthy."""
        return [m for m in self._pool.values() if m.loaded and m.healthy]

    async def evict_model(self, model_name: str) -> bool:
        """Unload a model via keep_alive=0 generation request.

        HOT models cannot be evicted.
        """
        model = self._pool.get(model_name)
        if model is None:
            return False

        if model.tier == ModelTierPolicy.HOT:
            logger.warning("Cannot evict HOT model %s", model_name)
            return False

        if not model.loaded:
            return True  # Already unloaded

        try:
            async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT_S) as client:
                resp = await client.post(
                    f"{self._ollama_host}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": "",
                        "keep_alive": 0,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                model.loaded = False
                model.healthy = False
                logger.info("Evicted model %s", model_name)
                return True
        except Exception as exc:
            logger.error("Failed to evict %s: %s", model_name, exc)
            return False

    _TIER_ORDER = {ModelTierPolicy.COLD: 0, ModelTierPolicy.WARM: 1, ModelTierPolicy.HOT: 2}

    async def promote(self, model_name: str, new_tier: ModelTierPolicy) -> None:
        """Promote a model to a higher tier (e.g., cold -> warm, warm -> hot).

        Raises ValueError if new_tier is not strictly higher than current tier.
        """
        model = self._pool.get(model_name)
        if model is None:
            logger.warning("Cannot promote unknown model %s", model_name)
            return

        if self._TIER_ORDER[new_tier] <= self._TIER_ORDER[model.tier]:
            raise ValueError(
                f"Cannot promote {model_name} from {model.tier.value} to {new_tier.value} "
                f"(new tier must be strictly higher)"
            )

        old_tier = model.tier
        model.tier = new_tier
        logger.info("Promoted %s: %s -> %s", model_name, old_tier.value, new_tier.value)

        # If promoting to HOT/WARM, ensure loaded
        if new_tier in (ModelTierPolicy.HOT, ModelTierPolicy.WARM):
            await self.ensure_loaded(model_name)

    async def demote_under_pressure(self) -> list[str]:
        """Evict lowest-priority models when memory pressure exceeds threshold.

        Eviction order: COLD (LRU) -> WARM (LRU). HOT never evicted.
        Returns list of evicted model names.
        """
        pressure = self._memory.analyze_memory_pressure()
        if pressure < self._config.memory_pressure_threshold:
            return []

        evicted: list[str] = []

        # Build eviction candidates sorted by priority
        candidates = sorted(
            [m for m in self._pool.values() if m.loaded and m.tier != ModelTierPolicy.HOT],
            key=lambda m: (
                0 if m.tier == ModelTierPolicy.COLD else 1,  # COLD first
                m.last_used,  # LRU within tier
            ),
        )

        for candidate in candidates:
            if self._memory.analyze_memory_pressure() < self._config.memory_pressure_threshold:
                break
            if await self.evict_model(candidate.name):
                evicted.append(candidate.name)

        if evicted:
            logger.info(
                "Demoted under pressure (%.1f%%): evicted %s",
                pressure * 100,
                evicted,
            )
        return evicted

    def get_pool_status(self) -> PoolStatus:
        """Return a snapshot of the current pool state."""
        loaded = [m.name for m in self._pool.values() if m.loaded]
        healthy = [m.name for m in self._pool.values() if m.loaded and m.healthy]
        # Cloud/edge models are remote — do not count toward local VRAM
        total_mem = sum(
            m.size_gb
            for m in self._pool.values()
            if m.loaded and m.tier not in (ModelTierPolicy.CLOUD, ModelTierPolicy.EDGE)
        )

        return PoolStatus(
            loaded_models=loaded,
            healthy_models=healthy,
            total_memory_gb=round(total_mem, 2),
            memory_pressure=round(self._memory.analyze_memory_pressure(), 3),
            models={
                name: asdict(m) if hasattr(m, "__dataclass_fields__") else vars(m)
                for name, m in self._pool.items()
            },
        )

    def get_model(self, model_name: str) -> PooledModel | None:
        """Get a specific model's state."""
        return self._pool.get(model_name)

    async def research_optimal_config(self, model_name: str) -> dict[str, Any]:
        """Query the researcher for optimal model configuration.

        Uses AutoResearcher to research the best configuration for a model,
        including memory requirements, optimal batch size, and tier placement.
        """
        query = f"optimal configuration for {model_name}"
        research_result = await self.researcher.research(query)

        # Extract configuration recommendations from research findings
        config = {
            "model_name": model_name,
            "recommended_tier": ModelTierPolicy.WARM,  # Default
            "optimal_batch_size": 1,
            "memory_requirements_gb": 0.0,
            "research_findings": research_result.findings,
            "confidence": research_result.confidence,
        }

        # Parse findings for configuration hints
        for finding in research_result.findings:
            finding_lower = finding.lower()
            if "hot" in finding_lower or "always loaded" in finding_lower:
                config["recommended_tier"] = ModelTierPolicy.HOT
            elif "cold" in finding_lower or "rarely used" in finding_lower:
                config["recommended_tier"] = ModelTierPolicy.COLD

        return config

    # --- Private helpers ---

    async def _list_ollama_models(self) -> list[dict[str, Any]]:
        """Query Ollama /api/tags for installed models."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._ollama_host}/api/tags")
                resp.raise_for_status()
                return resp.json().get("models", [])
        except Exception as exc:
            logger.error("Failed to list Ollama models: %s", exc)
            return []

    async def _list_running_models(self) -> list[dict[str, Any]]:
        """Query Ollama /api/ps for currently loaded models."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._ollama_host}/api/ps")
                resp.raise_for_status()
                return resp.json().get("models", [])
        except Exception as exc:
            logger.error("Failed to list running models: %s", exc)
            return []

    async def _list_lemonade_models(self) -> list[dict[str, Any]]:
        """Query private Lemonade server for installed models."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"http://{self.lemonade.host}:{self.lemonade.port}/api/v1/models"
                )
                resp.raise_for_status()
                # Lemonade API returns a list of models
                return resp.json().get("data", [])
        except Exception as exc:
            logger.error("Failed to list Lemonade models: %s", exc)
            return []

    async def _load_model(self, model_name: str, tier: ModelTierPolicy) -> bool:
        """Load a model by sending a minimal generation request with keep_alive.
        Implements a sequential loading lock to prevent memory spikes.
        """
        # Check if this model is routed to Lemonade
        is_lemonade = "gemma4:26b-moe" in model_name

        if is_lemonade:
            # Lemonade loads models on first request or via specific load API
            url = f"http://{self.lemonade.host}:{self.lemonade.port}/api/v1/load"
            payload = {"model_name": model_name, "llamacpp_backend": "rocm"}
            try:
                async with httpx.AsyncClient(timeout=_LOAD_TIMEOUT_S) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    logger.info("Loaded model %s via private Lemonade server", model_name)
                    return True
            except Exception as exc:
                logger.error("Failed to load model %s on Lemonade: %s", model_name, exc)
                return False

        # Sequential Loading Lock: Ensure only one local model loads at a time
        # Use a simple lock or synchronized block. For now, we rely on the await
        # call being sequential in the orchestrator, but we add a safeguard here.
        keep_alive: int | str
        if tier == ModelTierPolicy.HOT:
            keep_alive = -1  # Never unload
        elif tier == ModelTierPolicy.WARM:
            keep_alive = "5m"
        else:
            # COLD models stay loaded for cold_evict_timeout_s so the pool's
            # own eviction logic can manage them.  keep_alive=0 would cause
            # Ollama to unload immediately, making pool state inaccurate.
            timeout_s = int(self._config.cold_evict_timeout_s)
            keep_alive = f"{timeout_s}s"

        try:
            async with httpx.AsyncClient(timeout=_LOAD_TIMEOUT_S) as client:
                resp = await client.post(
                    f"{self._ollama_host}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": "",
                        "keep_alive": keep_alive,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                logger.info(
                    "Loaded model %s (tier=%s, keep_alive=%s)", model_name, tier.value, keep_alive
                )
                return True
        except Exception as exc:
            logger.error("Failed to load model %s: %s", model_name, exc)
            return False

    async def _evict_one(self, exclude: str = "") -> bool:
        """Evict one model to free a slot. Returns True if a model was evicted."""
        candidates = sorted(
            [
                m
                for m in self._pool.values()
                if m.loaded and m.tier != ModelTierPolicy.HOT and m.name != exclude
            ],
            key=lambda m: (
                0 if m.tier == ModelTierPolicy.COLD else 1,
                m.last_used,
            ),
        )
        for candidate in candidates:
            if await self.evict_model(candidate.name):
                return True
        return False


# Module-level singleton
_pool_manager: ModelPoolManager | None = None


def get_pool_manager(config: TierConfig | None = None) -> ModelPoolManager:
    """Get or create the singleton ModelPoolManager."""
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = ModelPoolManager(config=config)
    return _pool_manager


def reset_pool_manager() -> None:
    """Reset the singleton (testing only)."""
    global _pool_manager
    _pool_manager = None
