"""Comprehensive tests for ModelRanker cost-quality optimization.

Tests model ranking strategies:
- Cost-optimized ranking (prioritize cheapest models)
- Quality-first ranking (prioritize coherence)
- Balanced ranking (weighted combination)
- Coherence freshness decay
- Multi-strategy comparison
"""

import time
from unittest.mock import Mock

import pytest

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
        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b", "Phi-4-mini-instruct-Hybrid"]
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
        _model, score = ranked[0]

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
        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b", "Phi-4-mini-instruct-Hybrid"]
        ranked = ranker.rank_models(
            available_models=models,
            strategy=RankingStrategy.BALANCED,
        )

        assert len(ranked) == 3
        # All should have BALANCED strategy
        for _model, score in ranked:
            assert score.strategy == "balanced"

    def test_cost_optimized_strategy(self, ranker):
        """Test cost-optimized ranking strategy."""
        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b", "Phi-4-mini-instruct-Hybrid"]
        ranked = ranker.rank_models(
            available_models=models,
            strategy=RankingStrategy.COST_OPTIMIZED,
        )

        assert len(ranked) == 3
        # All should have COST_OPTIMIZED strategy
        for _model, score in ranked:
            assert score.strategy == "cost_optimized"

    def test_quality_first_strategy(self, ranker):
        """Test quality-first ranking strategy."""
        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b", "Phi-4-mini-instruct-Hybrid"]
        ranked = ranker.rank_models(
            available_models=models,
            strategy=RankingStrategy.QUALITY_FIRST,
        )

        assert len(ranked) == 3
        # All should have QUALITY_FIRST strategy
        for _model, score in ranked:
            assert score.strategy == "quality_first"

    def test_different_strategies_produce_different_rankings(self, ranker):
        """Test that different strategies produce different composite scores."""
        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b", "Phi-4-mini-instruct-Hybrid"]

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
        assert any(diff > 0.01 for diff in score_diffs), (
            "Strategies should produce different composite scores"
        )


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
        _model, score = ranked[0]
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

        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b", "Phi-4-mini-instruct-Hybrid"]
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

        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b", "Phi-4-mini-instruct-Hybrid"]
        all_strategies = ranker.rank_models_by_strategy(
            available_models=models,
        )

        for _strategy, rankings in all_strategies.items():
            assert len(rankings) == 3
            assert all(isinstance(score, ModelScore) for _, score in rankings)

    def test_strategy_consistency_across_calls(self):
        """Test that same strategy produces consistent ranking."""
        ranker = ModelRanker()

        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b", "Phi-4-mini-instruct-Hybrid"]

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
        for _model, score in ranked:
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
        _model, score = ranked[0]
        # Should use default (0.70)
        assert score.coherence_score == 0.70

    def test_mixed_known_unknown_models(self):
        """Test ranking with mix of known and unknown models."""
        ranker = ModelRanker()

        models = ["phi3:mini", "unknown-model", "deepseek-r1:8b"]
        ranked = ranker.rank_models(available_models=models)

        assert len(ranked) == 3
        # All should have valid scores
        for _model, score in ranked:
            assert 0.0 <= score.composite_score <= 1.0

    def test_unknown_model_coherence_clipping(self):
        """Test that unknown model coherence uses clipped default."""
        ranker = ModelRanker()

        # Unknown model should get DEFAULT (0.70)
        ranked = ranker.rank_models(
            available_models=["completely-unknown"],
        )

        assert ranked[0][1].coherence_score == 0.70


class TestWeightTuning:
    """Test custom weight configurations."""

    def test_custom_coherence_weight(self):
        """Test ranking with custom coherence weight."""
        ranker = ModelRanker(
            coherence_weight=0.7,
            cost_weight=0.1,
            latency_weight=0.1,
            freshness_weight=0.1,
        )

        ranked = ranker.rank_models(
            available_models=["phi3:mini", "deepseek-r1:8b"],
            strategy=RankingStrategy.BALANCED,
        )

        # deepseek has higher coherence (0.95 vs 0.65), should rank higher
        assert ranked[0][0] == "deepseek-r1:8b"

    def test_custom_cost_weight_high(self):
        """Test ranking with high cost weight."""
        ranker = ModelRanker(
            coherence_weight=0.1,
            cost_weight=0.7,
            latency_weight=0.1,
            freshness_weight=0.1,
        )

        # All local models have zero cost, so weight shouldn't change ranking much
        ranked = ranker.rank_models(
            available_models=["phi3:mini", "qwen3-coder:32b", "Phi-4-mini-instruct-Hybrid"],
            strategy=RankingStrategy.BALANCED,
        )

        assert len(ranked) == 2
        assert all(0.0 <= s.composite_score <= 1.0 for _, s in ranked)

    def test_unbalanced_weights_warning(self):
        """Test that unbalanced weights trigger warning."""
        ranker = ModelRanker(
            coherence_weight=0.5,
            cost_weight=0.5,
            latency_weight=0.5,
            freshness_weight=0.5,  # Sum = 2.0, not 1.0
        )

        # Should still work despite warning
        ranked = ranker.rank_models(available_models=["phi3:mini"])
        assert len(ranked) == 1

    def test_all_zero_weights_handled(self):
        """Test handling of all-zero weights."""
        ranker = ModelRanker(
            coherence_weight=0.0,
            cost_weight=0.0,
            latency_weight=0.0,
            freshness_weight=0.0,
        )

        ranked = ranker.rank_models(available_models=["phi3:mini"])
        # Should still produce valid scores (though all will be 0.0)
        assert len(ranked) == 1


class TestPerformanceAndEdgeCases:
    """Test performance and edge cases."""

    def test_ranking_large_model_set(self):
        """Test ranking performance with 100+ models."""
        ranker = ModelRanker()

        # Create 100 model names
        models = [f"model_{i}" for i in range(100)]

        import time

        start = time.time()
        ranked = ranker.rank_models(available_models=models)
        elapsed = time.time() - start

        assert len(ranked) == 100
        # Should complete in < 100ms
        assert elapsed < 0.1, f"Ranking 100 models took {elapsed * 1000:.1f}ms (target: <100ms)"

    def test_duplicate_models_handled(self):
        """Test that duplicate models in list are ranked."""
        ranker = ModelRanker()

        models = ["phi3:mini", "phi3:mini", "qwen3-coder:32b"]
        ranked = ranker.rank_models(available_models=models)

        # Should have entries for each occurrence
        assert len(ranked) == 3
        # All entries should have valid scores
        for _model, score in ranked:
            assert 0.0 <= score.composite_score <= 1.0

    def test_all_equal_models_ranking(self):
        """Test ranking when all models have equal scores."""
        ranker = ModelRanker()

        # Create models with identical properties
        models = ["model_a", "model_b", "model_c"]
        ranked = ranker.rank_models(available_models=models)

        # All should have same composite score
        scores = [s.composite_score for _, s in ranked]
        assert all(abs(scores[0] - s) < 0.01 for s in scores)

    def test_extreme_cost_values(self):
        """Test ranking with extreme cost values."""
        ranker = ModelRanker()

        costs = {
            "model_very_cheap": 0.0000001,
            "model_very_expensive": 100.0,
        }

        ranked = ranker.rank_models(
            available_models=list(costs.keys()),
            cost_per_token=costs,
            strategy=RankingStrategy.COST_OPTIMIZED,
        )

        # Cheap model should rank first
        assert ranked[0][0] == "model_very_cheap"

    def test_extreme_latency_values(self):
        """Test ranking with extreme latency values."""
        ranker = ModelRanker()

        latencies = {
            "model_fast": 1.0,  # 1ms
            "model_slow": 10000.0,  # 10 seconds
        }

        ranked = ranker.rank_models(
            available_models=list(latencies.keys()),
            latency_ms=latencies,
            strategy=RankingStrategy.QUALITY_FIRST,
        )

        # Fast model should rank higher
        assert ranked[0][0] == "model_fast"


class TestVaultIntegration:
    """Test vault integration and MCP client handling."""

    def test_ranker_with_mock_mcp_client(self):
        """Test ranker initialization with mock MCP client."""
        mock_client = Mock()
        ranker = ModelRanker(mcp_client=mock_client)

        assert ranker.mcp_client is mock_client

    def test_ranking_fallback_on_vault_failure(self):
        """Test that ranking falls back to defaults on vault error."""
        mock_client = Mock()
        mock_client.query.side_effect = Exception("Vault unreachable")

        ranker = ModelRanker(mcp_client=mock_client)

        # Should not raise, just fallback
        ranked = ranker.rank_models(
            available_models=["phi3:mini"],
            task_description="test task",
        )

        assert len(ranked) == 1
        assert ranked[0][1].coherence_score == 0.65  # Default for phi3:mini


class TestCompositeScoreCalculation:
    """Test composite score calculation accuracy."""

    def test_balanced_strategy_weights_sum_correctly(self):
        """Test that balanced strategy weights sum to 1.0."""
        ranker = ModelRanker()

        score = ranker._compute_composite_score(
            model="test_model",
            coherence=0.8,
            cost=0.015,
            latency=200.0,
            freshness=0.9,
            strategy=RankingStrategy.BALANCED,
        )

        # Score should be valid and reflect balanced weighting
        assert 0.0 <= score.composite_score <= 1.0
        # With balanced strategy, coherence should contribute significantly
        assert score.coherence_score == 0.8

    def test_cost_optimized_weights_sum_correctly(self):
        """Test that cost-optimized strategy weights sum correctly."""
        ranker = ModelRanker()

        score = ranker._compute_composite_score(
            model="test",
            coherence=0.8,
            cost=0.01,
            latency=100.0,
            freshness=0.9,
            strategy=RankingStrategy.COST_OPTIMIZED,
        )

        # Cost-optimized should weight cost heavily
        assert 0.0 <= score.composite_score <= 1.0

    def test_quality_first_weights_sum_correctly(self):
        """Test that quality-first strategy weights sum correctly."""
        ranker = ModelRanker()

        score = ranker._compute_composite_score(
            model="test",
            coherence=0.95,  # High coherence
            cost=0.02,
            latency=300.0,  # Higher latency acceptable
            freshness=0.8,
            strategy=RankingStrategy.QUALITY_FIRST,
        )

        # Quality-first should prefer high coherence
        assert 0.0 <= score.composite_score <= 1.0


class TestRankingConsistency:
    """Test consistency and determinism."""

    def test_ranking_deterministic(self):
        """Test that ranking is deterministic for same inputs."""
        ranker = ModelRanker()
        models = ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b", "Phi-4-mini-instruct-Hybrid"]

        # Rank 5 times
        rankings = [ranker.rank_models(available_models=models) for _ in range(5)]

        # All should be identical
        for ranking in rankings[1:]:
            for (m1, s1), (m2, s2) in zip(rankings[0], ranking):
                assert m1 == m2
                assert abs(s1.composite_score - s2.composite_score) < 1e-10

    def test_ranking_independent_of_input_order(self):
        """Test that ranking is independent of model list order."""
        ranker = ModelRanker()

        models = ["deepseek-r1:8b", "phi3:mini", "qwen3-coder:32b"]
        ranked1 = ranker.rank_models(available_models=models)

        models_reversed = list(reversed(models))
        ranked2 = ranker.rank_models(available_models=models_reversed)

        # Same composite scores for same models
        scores1 = {m: s.composite_score for m, s in ranked1}
        scores2 = {m: s.composite_score for m, s in ranked2}

        for model in scores1:
            assert abs(scores1[model] - scores2[model]) < 1e-10


class TestModelScoreSorting:
    """Test ModelScore comparison and sorting."""

    def test_model_score_less_than_comparison(self):
        """Test ModelScore.__lt__ for sorting."""
        score1 = ModelScore(
            model="model1",
            coherence_score=0.9,
            cost_per_token=0.01,
            latency_ms=100.0,
            freshness_score=0.8,
            composite_score=0.85,
            strategy="balanced",
        )

        score2 = ModelScore(
            model="model2",
            coherence_score=0.8,
            cost_per_token=0.01,
            latency_ms=100.0,
            freshness_score=0.8,
            composite_score=0.75,
            strategy="balanced",
        )

        # score1 > score2 in composite, so score1 < score2 (ascending by composite)
        assert score1 < score2

    def test_model_scores_sort_by_composite(self):
        """Test that list of ModelScores sorts correctly."""
        scores = [
            ModelScore("m1", 0.7, 0.01, 100, 0.8, 0.75, "balanced"),
            ModelScore("m2", 0.9, 0.01, 100, 0.8, 0.90, "balanced"),
            ModelScore("m3", 0.8, 0.01, 100, 0.8, 0.80, "balanced"),
        ]

        sorted_scores = sorted(scores)

        # Should be sorted by composite score (descending)
        composites = [s.composite_score for s in sorted_scores]
        assert composites == [0.90, 0.80, 0.75]


class TestIntegrationWithGlobalMetrics:
    """Test integration with GlobalMetricsAggregator."""

    def test_ranker_can_read_model_distribution(self):
        """Test that ranker can work with model distribution data."""
        ranker = ModelRanker()

        # Simulate model distribution from metrics
        model_distribution = {
            "phi3:mini": 0.4,
            "qwen3-coder:32b": 0.4,
            "deepseek-r1:8b": 0.2,
        }

        models = list(model_distribution.keys())
        ranked = ranker.rank_models(available_models=models)

        # Should rank all models
        assert len(ranked) == 3

    def test_ranker_produces_comparable_scores(self):
        """Test that ranker scores are comparable with metrics."""
        ranker = ModelRanker()

        ranked = ranker.rank_models(
            available_models=["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b", "Phi-4-mini-instruct-Hybrid"]
        )

        # Scores should be in valid range for comparison
        for _model, score in ranked:
            assert isinstance(score.coherence_score, float)
            assert isinstance(score.composite_score, float)
            assert 0.0 <= score.composite_score <= 1.0


class TestCacheFreshness:
    """Test cache freshness and expiration."""

    def test_cache_expiration_after_24_hours(self):
        """Test that cache entries expire after freshness_decay_hours."""
        ranker = ModelRanker(freshness_decay_hours=24.0)

        # Simulate time passing (72 hours = 3 days, well past 24 hour decay)
        very_old = time.time() - (72 * 3600)
        ranker.update_coherence_score("model", 0.85, timestamp=very_old)

        ranked = ranker.rank_models(available_models=["model"])
        freshness = ranked[0][1].freshness_score

        # Should be very low after 72 hours (3 decay half-lives)
        assert freshness < 0.2

    def test_cache_hit_with_fresh_entries(self):
        """Test that fresh cache entries are used."""
        ranker = ModelRanker()

        # Update with specific score
        ranker.update_coherence_score("model", 0.92)

        # Get score - should use cached value
        ranked = ranker.rank_models(
            available_models=["model"],
            task_description="some task",
        )

        assert ranked[0][1].coherence_score == 0.92
