"""Token-efficient Ollama client middleware.

Wraps ResilientOllamaClient with:
- Text-hash caching (SHA-256 of prompt+system -> cached response)
- Optional ContextHarness integration (prune long prompts before sending)
- Optional DynamicModelRouter for model selection
- Metrics tracking (cache_hits, cache_misses, tokens_saved, total_calls)

All dependencies are optional — the client degrades gracefully.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TokenMetrics:
    """Accumulated token efficiency metrics."""

    cache_hits: int = 0
    cache_misses: int = 0
    tokens_saved: int = 0
    total_calls: int = 0
    model_usage: dict[str, int] = field(default_factory=dict)

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "tokens_saved": self.tokens_saved,
            "total_calls": self.total_calls,
            "model_usage": dict(self.model_usage),
        }


class TokenEfficientClient:
    """Middleware wrapping ResilientOllamaClient with caching and context harnessing.

    Parameters
    ----------
    ollama_client : ResilientOllamaClient | None
        Underlying Ollama client. Created lazily if not provided.
    context_harness : ContextHarness | None
        Optional context pruner for long prompts.
    model_router : DynamicModelRouter | None
        Optional model selector based on task type and resources.
    cache_max_size : int
        Maximum number of cached prompt->response pairs.
    """

    def __init__(
        self,
        ollama_client: Any | None = None,
        context_harness: Any | None = None,
        model_router: Any | None = None,
        cache_max_size: int = 512,
    ) -> None:
        self._ollama = ollama_client
        self._harness = context_harness
        self._router = model_router
        self._cache: dict[str, str] = {}
        self._cache_max_size = cache_max_size
        self.metrics = TokenMetrics()

    @property
    def ollama(self) -> Any:
        """Lazy-initialize the underlying Ollama client."""
        if self._ollama is None:
            from cohezion.swarm.ollama_resilience import ResilientOllamaClient

            self._ollama = ResilientOllamaClient()
        return self._ollama

    @staticmethod
    def _cache_key(prompt: str, system: str | None, model: str | None) -> str:
        """Compute a deterministic SHA-256 cache key."""
        raw = f"{prompt}|{system or ''}|{model or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        task_type: str = "general",
        use_cache: bool = True,
        **kwargs: Any,
    ) -> str:
        """Generate a response with caching, harnessing, and routing.

        Parameters
        ----------
        prompt : str
            The user prompt.
        system : str | None
            Optional system prompt.
        model : str | None
            Override model name. If *model_router* is set and this is ``None``,
            the router picks the model.
        task_type : str
            Task hint for model routing (e.g. "coding", "analysis").
        use_cache : bool
            Whether to use the text-hash cache.
        **kwargs
            Forwarded to ``ResilientOllamaClient.generate()``.

        Returns
        -------
        str
            Generated text.
        """
        self.metrics.total_calls += 1

        # --- 1. Model routing (optional) ---
        routed_model = model
        if routed_model is None and self._router is not None:
            try:
                config = await self._router.select_optimal_model(
                    {"task_type": task_type, "context_length": len(prompt)}
                )
                routed_model = config.name
                logger.debug("Router selected model: %s", routed_model)
            except Exception:
                logger.warning("Model router failed, using default", exc_info=True)

        # --- 2. Cache lookup ---
        key = self._cache_key(prompt, system, routed_model)
        if use_cache and key in self._cache:
            cached = self._cache[key]
            self.metrics.cache_hits += 1
            self.metrics.tokens_saved += len(cached.split())
            logger.debug("Cache hit for key %s", key[:12])
            return cached

        self.metrics.cache_misses += 1

        # --- 3. Context harnessing (optional) ---
        effective_prompt = prompt
        effective_system = system
        if self._harness is not None:
            try:
                harnessed = self._harness.harness_prompt(prompt, system)
                effective_prompt = harnessed["prompt"]
                effective_system = harnessed["system"]
                logger.debug(
                    "Prompt harnessed: %d -> %d chars",
                    len(prompt),
                    len(effective_prompt),
                )
            except Exception:
                logger.warning(
                    "Context harness failed, using raw prompt", exc_info=True
                )

        # --- 4. Call underlying client ---
        result = await self.ollama.generate(
            prompt=effective_prompt,
            system=effective_system,
            model=routed_model,
            **kwargs,
        )

        # --- 5. Track model usage ---
        used_model = routed_model or getattr(self.ollama, "model", "unknown")
        self.metrics.model_usage[used_model] = (
            self.metrics.model_usage.get(used_model, 0) + 1
        )

        # --- 6. Cache result ---
        if use_cache:
            if len(self._cache) >= self._cache_max_size:
                # Evict oldest entry (FIFO via dict insertion order)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[key] = result

        return result

    def get_metrics(self) -> dict[str, Any]:
        """Return current token efficiency metrics."""
        return self.metrics.to_dict()

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self._cache.clear()

    async def close(self) -> None:
        """Close the underlying Ollama client."""
        if self._ollama is not None and hasattr(self._ollama, "close"):
            await self._ollama.close()
