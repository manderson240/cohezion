"""Token cache integration and optimization for TokenEfficientClient.

This module provides:
1. Seamless integration of MultiLayerCache into TokenEfficientClient
2. Automatic model-specific cache optimization
3. Cross-model cache sharing with safety checks
4. Metrics tracking and auto-tuning
5. Persistent cache for warm starts
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class CacheOptimizationConfig:
    """Configuration for token cache optimization."""

    semantic_cache_size: int = 2048
    context_pool_size: int = 128
    similarity_threshold: float = 0.65
    persistence_enabled: bool = True
    auto_tune_enabled: bool = True
    cross_model_sharing: bool = True
    defrag_threshold: float = 30.0  # Defrag when fragmentation > 30%


class TokenCacheOptimizer:
    """Optimize TokenEfficientClient's caching behavior.

    This class wraps MultiLayerCache and provides:
    - Automatic tuning based on workload
    - Cross-model cache sharing
    - KV-cache optimization
    - Performance monitoring
    """

    def __init__(self, config: CacheOptimizationConfig | None = None):
        """Initialize cache optimizer.

        Parameters
        ----------
        config : CacheOptimizationConfig | None
            Optimization configuration
        """
        self._config = config or CacheOptimizationConfig()
        self._multi_layer_cache = None
        self._model_stats: dict[str, dict[str, Any]] = {}
        self._operation_type_stats: dict[str, dict[str, Any]] = {}
        self._cross_model_safe_pairs: dict[str, set[str]] = {}

    def get_multi_layer_cache(self) -> Any:
        """Get or create MultiLayerCache instance.

        Returns
        -------
        MultiLayerCache
            Initialized cache instance
        """
        if self._multi_layer_cache is None:
            from cohezion.swarm.multi_layer_cache import MultiLayerCache

            self._multi_layer_cache = MultiLayerCache(
                semantic_max_entries=self._config.semantic_cache_size,
                context_pool_max=self._config.context_pool_size,
                persistence_enabled=self._config.persistence_enabled,
            )
        return self._multi_layer_cache

    def register_model_pair(self, model_a: str, model_b: str) -> None:
        """Register models as safe for cross-model cache sharing.

        Use this when two models share the same tokenizer or have
        compatible token spaces (e.g., different quantizations of same model).

        Parameters
        ----------
        model_a : str
            First model
        model_b : str
            Second model
        """
        if not self._config.cross_model_sharing:
            return

        self._cross_model_safe_pairs.setdefault(model_a, set()).add(model_b)
        self._cross_model_safe_pairs.setdefault(model_b, set()).add(model_a)

    def can_share_cache(self, model_a: str, model_b: str) -> bool:
        """Check if cache can be shared between models.

        Parameters
        ----------
        model_a : str
            Source model
        model_b : str
            Target model

        Returns
        -------
        bool
            Whether cache sharing is safe
        """
        if not self._config.cross_model_sharing:
            return False

        return model_b in self._cross_model_safe_pairs.get(model_a, set())

    def get_cached_or_none(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        operation_type: str = "general",
    ) -> tuple[str | None, str]:
        """Get cached response if available.

        Parameters
        ----------
        prompt : str
            User prompt
        system : str | None
            System prompt
        model : str | None
            Model name
        operation_type : str
            Operation type hint

        Returns
        -------
        tuple[str | None, str]
            (response, cache_layer_used)
        """
        cache = self.get_multi_layer_cache()
        response, layer = cache.get(
            prompt,
            system=system,
            model=model,
            operation_type=operation_type,
        )

        if response:
            self._update_model_stats(model or "unknown", layer, hit=True)
            logger.debug(
                "Cache hit via %s for model=%s operation=%s",
                layer,
                model,
                operation_type,
            )
        else:
            self._update_model_stats(model or "unknown", "miss", hit=False)

        return response, layer

    def cache_response(
        self,
        prompt: str,
        response: str,
        prompt_tokens: int,
        response_tokens: int,
        system: str | None = None,
        model: str | None = None,
        operation_type: str = "general",
    ) -> None:
        """Store response in cache.

        Parameters
        ----------
        prompt : str
            User prompt
        response : str
            Generated response
        prompt_tokens : int
            Number of prompt tokens
        response_tokens : int
            Number of response tokens
        system : str | None
            System prompt
        model : str | None
            Model name
        operation_type : str
            Operation type hint
        """
        cache = self.get_multi_layer_cache()
        cache.put(
            prompt,
            response,
            prompt_tokens,
            response_tokens,
            system=system,
            model=model,
        )

        self._update_operation_stats(
            operation_type,
            prompt_tokens + response_tokens,
            model or "unknown",
        )

        logger.debug(
            "Cached response for model=%s operation=%s (%d+%d tokens)",
            model,
            operation_type,
            prompt_tokens,
            response_tokens,
        )

    def _update_model_stats(self, model: str, cache_layer: str, hit: bool) -> None:
        """Update per-model cache statistics.

        Parameters
        ----------
        model : str
            Model name
        cache_layer : str
            Cache layer (exact, semantic, pool, miss)
        hit : bool
            Whether this was a hit
        """
        if model not in self._model_stats:
            self._model_stats[model] = {
                "total_requests": 0,
                "hits": 0,
                "by_layer": {},
            }

        stats = self._model_stats[model]
        stats["total_requests"] += 1

        if hit:
            stats["hits"] += 1
            stats["by_layer"][cache_layer] = stats["by_layer"].get(cache_layer, 0) + 1

    def _update_operation_stats(self, operation_type: str, total_tokens: int, model: str) -> None:
        """Update per-operation statistics.

        Parameters
        ----------
        operation_type : str
            Operation type
        total_tokens : int
            Total tokens processed
        model : str
            Model used
        """
        if operation_type not in self._operation_type_stats:
            self._operation_type_stats[operation_type] = {
                "executions": 0,
                "total_tokens": 0,
                "models_used": {},
            }

        stats = self._operation_type_stats[operation_type]
        stats["executions"] += 1
        stats["total_tokens"] += total_tokens
        stats["models_used"][model] = stats["models_used"].get(model, 0) + 1

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive caching metrics.

        Returns
        -------
        dict[str, Any]
            Metrics including cache effectiveness and recommendations
        """
        cache = self.get_multi_layer_cache()
        cache_stats = cache.get_statistics()

        return {
            "cache_statistics": cache_stats,
            "model_statistics": {
                model: {
                    "hit_rate": round(
                        stats["hits"] / stats["total_requests"]
                        if stats["total_requests"] > 0
                        else 0,
                        4,
                    ),
                    "total_requests": stats["total_requests"],
                    "hits": stats["hits"],
                    "by_layer": stats["by_layer"],
                }
                for model, stats in self._model_stats.items()
            },
            "operation_statistics": {
                op: {
                    "executions": stats["executions"],
                    "avg_tokens": round(stats["total_tokens"] / stats["executions"], 0),
                    "models_used": stats["models_used"],
                }
                for op, stats in self._operation_type_stats.items()
            },
            "cross_model_sharing": {
                "enabled": self._config.cross_model_sharing,
                "safe_pairs": {k: list(v) for k, v in self._cross_model_safe_pairs.items()},
            },
        }

    async def optimize(self) -> dict[str, Any]:
        """Run optimization pass.

        Returns
        -------
        dict[str, Any]
            Optimization results and recommendations
        """
        cache = self.get_multi_layer_cache()
        recommendations = await cache.optimize()

        # Add model-specific recommendations
        recommendations["model_recommendations"] = self._get_model_recommendations()

        return dict(recommendations)

    def _get_model_recommendations(self) -> dict[str, list[str]]:
        """Get model-specific optimization recommendations.

        Returns
        -------
        dict[str, list[str]]
            Model -> list of recommendations
        """
        recommendations: dict[str, list[str]] = {}

        for model, stats in self._model_stats.items():
            model_recs: list[str] = []
            hit_rate = stats["hits"] / stats["total_requests"] if stats["total_requests"] > 0 else 0

            if hit_rate < 0.3:
                model_recs.append("Low hit rate - consider tweaking similarity_threshold")

            if hit_rate > 0.8:
                model_recs.append("High hit rate - consider expanding cache size")

            if stats["total_requests"] < 10:
                model_recs.append("Limited data - continue collecting metrics")

            if model_recs:
                recommendations[model] = model_recs

        return recommendations

    def clear(self) -> None:
        """Clear all caches and statistics."""
        if self._multi_layer_cache:
            self._multi_layer_cache.clear()

        self._model_stats.clear()
        self._operation_type_stats.clear()

    def set_similarity_threshold(self, threshold: float) -> None:
        """Adjust semantic similarity threshold.

        Lower threshold = more fuzzy matches but lower precision
        Higher threshold = fewer matches but higher precision

        Parameters
        ----------
        threshold : float
            Similarity threshold (0-1), recommended 0.6-0.8
        """
        cache = self.get_multi_layer_cache()
        cache._semantic_cache._similarity_threshold = threshold
        logger.info("Updated similarity threshold to %.2f", threshold)


# Global optimizer instance
_token_cache_optimizer: TokenCacheOptimizer | None = None


def get_token_cache_optimizer(
    config: CacheOptimizationConfig | None = None,
) -> TokenCacheOptimizer:
    """Get or create global token cache optimizer.

    Parameters
    ----------
    config : CacheOptimizationConfig | None
        Configuration (only used on first call)

    Returns
    -------
    TokenCacheOptimizer
        Global optimizer instance
    """
    global _token_cache_optimizer
    if _token_cache_optimizer is None:
        _token_cache_optimizer = TokenCacheOptimizer(config)
    return _token_cache_optimizer
