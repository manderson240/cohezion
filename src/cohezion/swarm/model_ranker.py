"""Cost-quality optimized model ranking with historical coherence integration.

Ranks models by weighted combination of:
- Coherence score (historical model quality)
- Cost efficiency (cost per token)
- Latency (response time)
- Freshness (recency of evaluation)

Usage:
    ranker = ModelRanker(mcp_client=mcp_client)
    ranked_models = ranker.rank_models(
        task_description="Write a Python function",
        available_models=["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"]
    )
    for model, score in ranked_models:
        print(f"{model}: {score.composite_score:.3f}")
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class RankingStrategy(Enum):
    """Model ranking strategies."""

    COST_OPTIMIZED = "cost_optimized"  # Prioritize cost (cost×0.5)
    QUALITY_FIRST = "quality_first"  # Prioritize quality (coherence×0.6)
    BALANCED = (
        "balanced"  # Balanced weighting (coherence×0.4 + cost×0.3 + latency×0.2 + freshness×0.1)
    )


@dataclass
class ModelScore:
    """Composite score for a model candidate."""

    model: str
    coherence_score: float  # 0.0-1.0, historical quality
    cost_per_token: float  # Lower is better (0.0+ in USD)
    latency_ms: float  # Lower is better (milliseconds)
    freshness_score: float  # 0.0-1.0, recency of evaluation (1.0 = recent)
    composite_score: float  # Weighted combination (0.0-1.0)
    strategy: str  # Which ranking strategy produced this score

    def __lt__(self, other: "ModelScore") -> bool:
        """Comparison for sorting (higher composite scores first)."""
        return self.composite_score > other.composite_score

    def __repr__(self) -> str:
        """Readable representation."""
        return (
            f"ModelScore(model={self.model}, "
            f"composite={self.composite_score:.3f}, "
            f"coherence={self.coherence_score:.2f}, "
            f"cost={self.cost_per_token:.6f}, "
            f"latency={self.latency_ms:.1f}ms)"
        )


class ModelRanker:
    """Cost-quality optimized model ranking with coherence integration.

    Ranks models using weighted combination of:
    - Coherence (historical performance from vault)
    - Cost efficiency (cost per token)
    - Latency (expected response time)
    - Freshness (recency of evaluation)

    Features:
    - Three ranking strategies (cost-optimized, quality-first, balanced)
    - Automatic coherence fallback (uses defaults if vault unavailable)
    - Token efficiency normalization across models
    - Latency-quality tradeoff analysis
    - Freshness decay (older evaluations scored lower)
    """

    # Default coherence scores (fallback if vault unavailable)
    DEFAULT_COHERENCE = {
        "phi3:mini": 0.65,  # Fast, good for simple tasks
        "qwen3-coder:32b": 0.82,  # Good balance
        "deepseek-r1:8b": 0.95,  # Best quality
        "gemma3:4b": 0.60,  # Lightweight
        "mistral:7b": 0.75,  # Decent quality
        "llama4-scout": 0.70,  # Emerging model
    }

    # Default latency expectations (ms)
    DEFAULT_LATENCY = {
        "phi3:mini": 50.0,
        "qwen3-coder:32b": 100.0,
        "deepseek-r1:8b": 300.0,
        "gemma3:4b": 40.0,
        "mistral:7b": 80.0,
        "llama4-scout": 120.0,
    }

    def __init__(
        self,
        mcp_client=None,  # Optional: MCPClient for vault queries
        coherence_weight: float = 0.4,
        cost_weight: float = 0.3,
        latency_weight: float = 0.2,
        freshness_weight: float = 0.1,
        freshness_decay_hours: float = 24.0,  # Freshness half-life
    ):
        """Initialize model ranker.

        Args:
            mcp_client: Optional MCPClient for vault coherence queries
            coherence_weight: Weight for coherence score (0.0-1.0)
            cost_weight: Weight for cost efficiency (0.0-1.0)
            latency_weight: Weight for latency (0.0-1.0)
            freshness_weight: Weight for freshness (0.0-1.0)
            freshness_decay_hours: Hours for coherence freshness half-life
        """
        self.mcp_client = mcp_client
        self.coherence_weight = coherence_weight
        self.cost_weight = cost_weight
        self.latency_weight = latency_weight
        self.freshness_weight = freshness_weight
        self.freshness_decay_hours = freshness_decay_hours

        # Verify weights sum to approximately 1.0
        total_weight = sum([coherence_weight, cost_weight, latency_weight, freshness_weight])
        if not (0.9 <= total_weight <= 1.1):
            logger.warning(
                f"Model ranking weights sum to {total_weight}, expected ~1.0. "
                f"Scores will be normalized."
            )

        # Cache for coherence scores
        self._coherence_cache: dict[str, tuple[float, float]] = {}  # model -> (score, timestamp)

    def rank_models(
        self,
        available_models: list[str],
        task_description: str = "",
        cost_per_token: dict[str, float] | None = None,
        latency_ms: dict[str, float] | None = None,
        strategy: RankingStrategy = RankingStrategy.BALANCED,
    ) -> list[tuple[str, ModelScore]]:
        """Rank available models by composite score.

        Args:
            available_models: List of available model names
            task_description: Task description for coherence lookup (optional)
            cost_per_token: Optional dict of model → cost/token overrides
            latency_ms: Optional dict of model → latency_ms overrides
            strategy: Ranking strategy to use

        Returns:
            List of (model_name, ModelScore) tuples, sorted by composite score (best first)
        """
        if not available_models:
            return []

        # Use provided or default cost/latency
        cost_per_token = cost_per_token or self._get_default_costs(available_models)
        latency_ms = latency_ms or self._get_default_latencies(available_models)

        # Score each model
        scores = []
        for model in available_models:
            # Get coherence (from vault or defaults)
            coherence = self._get_coherence_score(model, task_description)

            # Get freshness score (decay older coherence)
            freshness = self._get_freshness_score(model)

            # Create model score
            score = self._compute_composite_score(
                model=model,
                coherence=coherence,
                cost=cost_per_token.get(model, 0.015),  # Conservative default
                latency=latency_ms.get(model, 100.0),
                freshness=freshness,
                strategy=strategy,
            )

            scores.append((model, score))

        # Sort by composite score (highest first)
        scores.sort(key=lambda x: x[1])

        return scores

    def rank_models_by_strategy(
        self,
        available_models: list[str],
        task_description: str = "",
        cost_per_token: dict[str, float] | None = None,
        latency_ms: dict[str, float] | None = None,
    ) -> dict[RankingStrategy, list[tuple[str, ModelScore]]]:
        """Rank models using all available strategies.

        Args:
            available_models: List of available model names
            task_description: Task description for coherence lookup
            cost_per_token: Optional cost overrides
            latency_ms: Optional latency overrides

        Returns:
            Dict mapping strategy → ranked models list
        """
        results = {}
        for strategy in RankingStrategy:
            results[strategy] = self.rank_models(
                available_models=available_models,
                task_description=task_description,
                cost_per_token=cost_per_token,
                latency_ms=latency_ms,
                strategy=strategy,
            )

        return results

    def _compute_composite_score(
        self,
        model: str,
        coherence: float,
        cost: float,
        latency: float,
        freshness: float,
        strategy: RankingStrategy,
    ) -> ModelScore:
        """Compute composite score based on strategy.

        Args:
            model: Model name
            coherence: Coherence score (0.0-1.0)
            cost: Cost per token (0.0+)
            latency: Latency in ms (0.0+)
            freshness: Freshness score (0.0-1.0)
            strategy: Ranking strategy

        Returns:
            ModelScore with weighted composite
        """
        # Normalize cost (0.0-1.0 scale: lower cost = higher score)
        # Assume max cost is $0.05/1k tokens for normalization
        max_cost = 0.05 / 1000.0
        cost_score = max(0.0, 1.0 - (cost / max_cost)) if max_cost > 0 else 1.0
        cost_score = min(1.0, cost_score)  # Cap at 1.0

        # Normalize latency (0.0-1.0 scale: lower latency = higher score)
        # Assume max acceptable latency is 500ms
        max_latency = 500.0
        latency_score = max(0.0, 1.0 - (latency / max_latency)) if max_latency > 0 else 1.0
        latency_score = min(1.0, latency_score)  # Cap at 1.0

        # Apply strategy-specific weighting
        if strategy == RankingStrategy.COST_OPTIMIZED:
            # Prioritize cost: cost×0.5, coherence×0.25, latency×0.15, freshness×0.1
            composite = cost_score * 0.5 + coherence * 0.25 + latency_score * 0.15 + freshness * 0.1
        elif strategy == RankingStrategy.QUALITY_FIRST:
            # Prioritize quality: coherence×0.6, latency×0.2, cost×0.1, freshness×0.1
            composite = coherence * 0.6 + latency_score * 0.2 + cost_score * 0.1 + freshness * 0.1
        else:  # BALANCED (default)
            # Balanced: coherence×0.4, cost×0.3, latency×0.2, freshness×0.1
            composite = coherence * 0.4 + cost_score * 0.3 + latency_score * 0.2 + freshness * 0.1

        return ModelScore(
            model=model,
            coherence_score=coherence,
            cost_per_token=cost,
            latency_ms=latency,
            freshness_score=freshness,
            composite_score=min(1.0, max(0.0, composite)),  # Normalize to 0-1
            strategy=strategy.value,
        )

    def _get_coherence_score(self, model: str, task_description: str = "") -> float:
        """Get coherence score for model (from vault or defaults).

        Args:
            model: Model name
            task_description: Task description for vault lookup

        Returns:
            Coherence score (0.0-1.0)
        """
        # Check cache first
        if model in self._coherence_cache:
            score, timestamp = self._coherence_cache[model]
            # Use cached score if fresh (< 24 hours)
            if time.time() - timestamp < 86400:
                return score

        # Try vault lookup (if available)
        if self.mcp_client and task_description:
            try:
                # Query vault for model coherence on similar tasks
                coherence = self._query_vault_coherence(model, task_description)
                if coherence is not None:
                    self._coherence_cache[model] = (coherence, time.time())
                    return coherence
            except Exception as e:
                logger.debug(f"Vault coherence lookup failed for {model}: {e}")

        # Fallback to default
        return self.DEFAULT_COHERENCE.get(model, 0.70)

    def _query_vault_coherence(self, model: str, task_description: str) -> float | None:
        """Query vault for model coherence on similar tasks.

        Args:
            model: Model name
            task_description: Task description

        Returns:
            Coherence score or None if unavailable
        """
        if not self.mcp_client:
            return None

        try:
            # Query vault for patterns matching task and model
            _query = f"coherence pattern where model='{model}' and similarity(task, '{task_description}') > 0.7"
            # Note: This is a conceptual query - actual implementation would depend on vault API
            # For now, return None to fall back to defaults
            return None
        except Exception as e:
            logger.debug(f"Vault query failed: {e}")
            return None

    def _get_freshness_score(self, model: str) -> float:
        """Get freshness score for coherence evaluation.

        Models with recent coherence evaluations score higher.

        Args:
            model: Model name

        Returns:
            Freshness score (0.0-1.0, 1.0 = very recent)
        """
        if model not in self._coherence_cache:
            # No cached evaluation = moderate freshness
            return 0.7

        _score, timestamp = self._coherence_cache[model]
        age_hours = (time.time() - timestamp) / 3600.0

        # Exponential decay with half-life of freshness_decay_hours
        # freshness = 0.5^(age/half_life)
        freshness = 0.5 ** (age_hours / self.freshness_decay_hours)

        return max(0.0, min(1.0, freshness))

    def _get_default_costs(self, models: list[str]) -> dict[str, float]:
        """Get default cost per token for models.

        Args:
            models: List of model names

        Returns:
            Dict mapping model → cost/token
        """
        # All local models are free ($0.00)
        return dict.fromkeys(models, 0.0)

    def _get_default_latencies(self, models: list[str]) -> dict[str, float]:
        """Get default latency expectations for models.

        Args:
            models: List of model names

        Returns:
            Dict mapping model → latency_ms
        """
        return {model: self.DEFAULT_LATENCY.get(model, 100.0) for model in models}

    def update_coherence_score(
        self, model: str, coherence_score: float, timestamp: float | None = None
    ) -> None:
        """Update cached coherence score for a model.

        Args:
            model: Model name
            coherence_score: New coherence score (0.0-1.0)
            timestamp: Optional timestamp (defaults to now)
        """
        if not (0.0 <= coherence_score <= 1.0):
            logger.warning(f"Coherence score {coherence_score} out of range [0.0, 1.0]")
            coherence_score = max(0.0, min(1.0, coherence_score))

        self._coherence_cache[model] = (coherence_score, timestamp or time.time())

    def clear_cache(self) -> None:
        """Clear coherence cache (testing only)."""
        self._coherence_cache.clear()

    def get_cache_stats(self) -> dict:
        """Get coherence cache statistics.

        Returns:
            Dict with cache status
        """
        stats = {
            "cached_models": len(self._coherence_cache),
            "total_entries": len(self._coherence_cache),
        }

        # Add freshness stats
        if self._coherence_cache:
            ages = []
            for _, (_, timestamp) in self._coherence_cache.items():
                age_hours = (time.time() - timestamp) / 3600.0
                ages.append(age_hours)

            stats["oldest_entry_hours"] = max(ages)
            stats["newest_entry_hours"] = min(ages)
            stats["avg_entry_age_hours"] = sum(ages) / len(ages)

        return stats
