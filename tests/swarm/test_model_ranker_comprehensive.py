"""Comprehensive tests for ModelRanker cost-quality optimization.

Tests model ranking strategies:
- Cost-optimized ranking (prioritize cheapest models)
- Quality-first ranking (prioritize coherence)
- Balanced ranking (weighted combination)
- Coherence freshness decay
- Multi-strategy comparison
"""

import pytest
import time
from unittest.mock import Mock, MagicMock

from cohezion.swarm.model_ranker import (
    ModelRanker,
    ModelScore,
    RankingStrategy,
)


class TestModelRankerBasics:
    """Test basic model ranking functionality."""

    @pytest.fixture
    def ranker(self):
        """Create a basic model ranker."""
        return ModelRanker()

    def test_ranker_initialization(self, ranker):
        """Test ranker initializes with default weights."""
        assert ranker.coherence_weight == 0.4
        assert ranker.cost_weight == 0.3
        assert ranker.latency_weight == 0.2
        assert ranker.freshness_weight == 0.1

    def test_rank_single_model(self, ranker):
        """Test ranking a single model."""
        ranked = ranker.rank_models(
            available_models=["phi3:mini"],
        )

        assert len(ranked) == 1
        model, score = ranked[0]
        assert model == "phi3:mini"
        assert isinstance(score, ModelScore)
        assert 0.0 <= score.composite_score <= 1.0

    def test_rank_multiple_models(self, ranker):
        """Test ranking multiple models."""
        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"]
        ranked = ranker.rank_models(available_models=models)

        assert len(ranked) == 3
        # Should be sorted by composite score (highest first)
        for i in range(len(ranked) - 1):
            assert ranked[i][1].composite_score >= ranked[i + 1][1].composite_score

    def test_empty_model_list(self, ranker):
        """Test ranking with no available models."""
        ranked = ranker.rank_models(available_models=[])
        assert len(ranked) == 0

    def test_model_score_representation(self, ranker):
        """Test ModelScore string representation."""
        ranked = ranker.rank_models(available_models=["phi3:mini"])
        model, score = ranked[0]

        repr_str = repr(score)
        assert "ModelScore" in repr_str
        assert "phi3:mini" in repr_str
        assert "composite=" in repr_str


class TestRankingStrategies:
    """Test different ranking strategies."""

    @pytest.fixture
    def ranker(self):
        """Create a ranker with test weights."""
        return ModelRanker(
            coherence_weight=0.4,
            cost_weight=0.3,
            latency_weight=0.2,
            freshness_weight=0.1,
        )

    def test_balanced_strategy(self, ranker):
        """Test balanced ranking strategy."""
        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"]
        ranked = ranker.rank_models(
            available_models=models,
            strategy=RankingStrategy.BALANCED,
        )

        assert len(ranked) == 3
        # All should have BALANCED strategy
        for model, score in ranked:
            assert score.strategy == "balanced"

    def test_cost_optimized_strategy(self, ranker):
        """Test cost-optimized ranking strategy."""
        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"]
        ranked = ranker.rank_models(
            available_models=models,
            strategy=RankingStrategy.COST_OPTIMIZED,
        )

        assert len(ranked) == 3
        # All should have COST_OPTIMIZED strategy
        for model, score in ranked:
            assert score.strategy == "cost_optimized"

    def test_quality_first_strategy(self, ranker):
        """Test quality-first ranking strategy."""
        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"]
        ranked = ranker.rank_models(
            available_models=models,
            strategy=RankingStrategy.QUALITY_FIRST,
        )

        assert len(ranked) == 3
        # All should have QUALITY_FIRST strategy
        for model, score in ranked:
            assert score.strategy == "quality_first"

    def test_different_strategies_produce_different_rankings(self, ranker):
        """Test that different strategies produce different composite scores."""
        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"]

        cost_ranked = ranker.rank_models(
            available_models=models,
            strategy=RankingStrategy.COST_OPTIMIZED,
        )

        quality_ranked = ranker.rank_models(
            available_models=models,
            strategy=RankingStrategy.QUALITY_FIRST,
        )

        # Extract composite scores
        cost_scores = {m: s.composite_score for m, s in cost_ranked}
        quality_scores = {m: s.composite_score for m, s in quality_ranked}

        # Scores should differ for at least some models
        # (different weighting produces different scores)
        score_diffs = [abs(cost_scores[m] - quality_scores[m]) for m in models]
        assert any(diff > 0.01 for diff in score_diffs), "Strategies should produce different composite scores"


class TestCoherenceScoring:
    """Test coherence score handling."""

    def test_default_coherence_values(self):
        """Test default coherence scores for models."""
        ranker = ModelRanker()

        # Check default scores exist
        assert ranker.DEFAULT_COHERENCE["phi3:mini"] == 0.65
        assert ranker.DEFAULT_COHERENCE["qwen3-coder:32b"] == 0.82
        assert ranker.DEFAULT_COHERENCE["deepseek-r1:8b"] == 0.95

    def test_coherence_fallback_when_vault_unavailable(self):
        """Test that coherence falls back to defaults when vault unavailable."""
        ranker = ModelRanker(mcp_client=None)

        ranked = ranker.rank_models(
            available_models=["deepseek-r1:8b"],
            task_description="Some task",
        )

        assert len(ranked) == 1
        model, score = ranked[0]
        # Should use default coherence
        assert score.coherence_score == 0.95

    def test_update_coherence_score(self):
        """Test updating cached coherence score."""
        ranker = ModelRanker()

        # Update score
        ranker.update_coherence_score("test-model", 0.88)

        # Score should be updated
        ranked = ranker.rank_models(available_models=["test-model"])
        assert ranked[0][1].coherence_score == 0.88

    def test_update_coherence_with_timestamp(self):
        """Test updating coherence with explicit timestamp."""
        ranker = ModelRanker()

        old_time = time.time() - 3600  # 1 hour ago
        ranker.update_coherence_score("test-model", 0.75, timestamp=old_time)

        # Freshness should be low (old evaluation)
        ranked = ranker.rank_models(available_models=["test-model"])
        assert ranked[0][1].freshness_score < 1.0

    def test_coherence_clipping_range(self):
        """Test that coherence scores are clipped to [0.0, 1.0]."""
        ranker = ModelRanker()

        # Update with out-of-range values
        ranker.update_coherence_score("model1", 1.5)  # Too high
        ranker.update_coherence_score("model2", -0.5)  # Too low

        # Should be clipped
        assert ranker._coherence_cache["model1"][0] == 1.0
        assert ranker._coherence_cache["model2"][0] == 0.0


class TestFreshnessDecay:
    """Test freshness score decay over time."""

    def test_fresh_evaluation_high_score(self):
        """Test that recent evaluations get high freshness."""
        ranker = ModelRanker(freshness_decay_hours=24.0)

        # Update with current time (fresh)
        ranker.update_coherence_score("model", 0.80)

        ranked = ranker.rank_models(available_models=["model"])
        freshness = ranked[0][1].freshness_score

        # Should be high (fresh)
        assert freshness >= 0.9

    def test_old_evaluation_low_score(self):
        """Test that old evaluations get lower freshness."""
        ranker = ModelRanker(freshness_decay_hours=24.0)

        # Update with old time (24+ hours ago)
        old_time = time.time() - 86400  # Exactly 24 hours
        ranker.update_coherence_score("model", 0.80, timestamp=old_time)

        ranked = ranker.rank_models(available_models=["model"])
        freshness = ranked[0][1].freshness_score

        # Should be ~0.5 (half-life reached)
        assert 0.4 <= freshness <= 0.6

    def test_very_old_evaluation_minimal_freshness(self):
        """Test that very old evaluations get minimal freshness."""
        ranker = ModelRanker(freshness_decay_hours=24.0)

        # Update with very old time (72+ hours ago)
        very_old_time = time.time() - 259200  # 72 hours
        ranker.update_coherence_score("model", 0.80, timestamp=very_old_time)

        ranked = ranker.rank_models(available_models=["model"])
        freshness = ranked[0][1].freshness_score

        # Should be very low (< 0.15)
        assert freshness < 0.15

    def test_freshness_decay_rate(self):
        """Test that freshness decays at exponential rate."""
        ranker = ModelRanker(freshness_decay_hours=24.0)

        # Measure freshness at different ages
        hours_list = [0, 12, 24, 36, 48]
        freshness_scores = []

        for hours_ago in hours_list:
            old_time = time.time() - (hours_ago * 3600)
            ranker.update_coherence_score("model", 0.80, timestamp=old_time)

            ranked = ranker.rank_models(available_models=["model"])
            freshness_scores.append(ranked[0][1].freshness_score)

        # Freshness should decay monotonically
        for i in range(len(freshness_scores) - 1):
            assert freshness_scores[i] >= freshness_scores[i + 1]


class TestMultiStrategyComparison:
    """Test comparing rankings across strategies."""

    def test_rank_models_by_all_strategies(self):
        """Test ranking by all strategies simultaneously."""
        ranker = ModelRanker()

        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"]
        all_strategies = ranker.rank_models_by_strategy(
            available_models=models,
        )

        # Should have results for all 3 strategies
        assert len(all_strategies) == 3
        assert RankingStrategy.COST_OPTIMIZED in all_strategies
        assert RankingStrategy.QUALITY_FIRST in all_strategies
        assert RankingStrategy.BALANCED in all_strategies

    def test_each_strategy_produces_ranking(self):
        """Test that each strategy produces a complete ranking."""
        ranker = ModelRanker()

        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"]
        all_strategies = ranker.rank_models_by_strategy(
            available_models=models,
        )

        for strategy, rankings in all_strategies.items():
            assert len(rankings) == 3
            assert all(isinstance(score, ModelScore) for _, score in rankings)

    def test_strategy_consistency_across_calls(self):
        """Test that same strategy produces consistent ranking."""
        ranker = ModelRanker()

        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"]

        # Rank twice
        ranking1 = ranker.rank_models(
            available_models=models,
            strategy=RankingStrategy.BALANCED,
        )

        ranking2 = ranker.rank_models(
            available_models=models,
            strategy=RankingStrategy.BALANCED,
        )

        # Should be identical
        for (m1, s1), (m2, s2) in zip(ranking1, ranking2):
            assert m1 == m2
            assert s1.composite_score == s2.composite_score


class TestCostAndLatencyNormalization:
    """Test cost and latency score normalization."""

    def test_lower_cost_higher_score(self):
        """Test that lower cost produces higher cost score."""
        ranker = ModelRanker()

        # Rank with explicit costs
        costs = {
            "model1": 0.001,  # Low cost
            "model2": 0.01,  # Higher cost
        }

        ranked = ranker.rank_models(
            available_models=list(costs.keys()),
            cost_per_token=costs,
            strategy=RankingStrategy.COST_OPTIMIZED,
        )

        # Lower cost model should rank higher (better composite score)
        assert ranked[0][0] == "model1"

    def test_lower_latency_higher_score(self):
        """Test that lower latency produces higher latency score."""
        ranker = ModelRanker()

        # Rank with explicit latencies
        latencies = {
            "model1": 50.0,  # Fast
            "model2": 300.0,  # Slow
        }

        ranked = ranker.rank_models(
            available_models=list(latencies.keys()),
            latency_ms=latencies,
            strategy=RankingStrategy.QUALITY_FIRST,  # Quality prioritizes latency
        )

        # Faster model should rank better
        assert ranked[0][0] == "model1"

    def test_zero_cost_normalization(self):
        """Test that zero cost (local models) normalizes correctly."""
        ranker = ModelRanker()

        # All local models have zero cost
        costs = {
            "model1": 0.0,
            "model2": 0.0,
            "model3": 0.0,
        }

        ranked = ranker.rank_models(
            available_models=list(costs.keys()),
            cost_per_token=costs,
            strategy=RankingStrategy.COST_OPTIMIZED,
        )

        # All should have valid scores despite zero cost
        for model, score in ranked:
            assert 0.0 <= score.composite_score <= 1.0


class TestCacheManagement:
    """Test coherence cache management."""

    def test_cache_initialization(self):
        """Test cache initializes empty."""
        ranker = ModelRanker()
        assert len(ranker._coherence_cache) == 0

    def test_cache_statistics(self):
        """Test cache statistics reporting."""
        ranker = ModelRanker()

        # Add some entries
        ranker.update_coherence_score("model1", 0.75)
        ranker.update_coherence_score("model2", 0.85)

        stats = ranker.get_cache_stats()

        assert stats["cached_models"] == 2
        assert stats["total_entries"] == 2
        assert "oldest_entry_hours" in stats
        assert "newest_entry_hours" in stats

    def test_cache_clear(self):
        """Test clearing the cache."""
        ranker = ModelRanker()

        # Add entries
        ranker.update_coherence_score("model1", 0.75)
        ranker.update_coherence_score("model2", 0.85)

        # Clear
        ranker.clear_cache()

        assert len(ranker._coherence_cache) == 0

    def test_empty_cache_statistics(self):
        """Test cache statistics with empty cache."""
        ranker = ModelRanker()

        stats = ranker.get_cache_stats()

        assert stats["cached_models"] == 0
        assert stats["total_entries"] == 0
        assert "oldest_entry_hours" not in stats  # No entries to measure


class TestUnknownModels:
    """Test handling of unknown models."""

    def test_unknown_model_uses_defaults(self):
        """Test that unknown models use default coherence."""
        ranker = ModelRanker()

        ranked = ranker.rank_models(
            available_models=["unknown-model-xyz"],
        )

        assert len(ranked) == 1
        model, score = ranked[0]
        # Should use default (0.70)
        assert score.coherence_score == 0.70

    def test_mixed_known_unknown_models(self):
        """Test ranking with mix of known and unknown models."""
        ranker = ModelRanker()

        models = ["phi3:mini", "unknown-model", "deepseek-r1:8b"]
        ranked = ranker.rank_models(available_models=models)

        assert len(ranked) == 3
        # All should have valid scores
        for model, score in ranked:
            assert 0.0 <= score.composite_score <= 1.0

    def test_unknown_model_coherence_clipping(self):
        """Test that unknown model coherence uses clipped default."""
        ranker = ModelRanker()

        # Unknown model should get DEFAULT (0.70)
        ranked = ranker.rank_models(
            available_models=["completely-unknown"],
        )

        assert ranked[0][1].coherence_score == 0.70
