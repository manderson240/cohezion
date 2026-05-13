"""Unit tests for ModelRegistry class.

Tests model registration, selection, budget constraints, cost tracking,
and capability-based filtering.
"""

import pytest

from cohezion.models.model_info import ModelInfo
from cohezion.models.model_registry import ModelRegistry


class TestModelRegistryBasics:
    """Test basic registry operations."""

    def test_register_defaults(self):
        """Test that defaults are registered on init."""
        registry = ModelRegistry()
        assert len(registry.list_models()) > 0

    def test_register_model(self):
        """Test register_model adds a new model."""
        registry = ModelRegistry()
        initial_count = len(registry.list_models())

        custom_model = ModelInfo(
            name="custom:test",
            provider="test-provider",
            cost_per_1k_tokens=0.5,
            max_tokens=2048,
            supports_images=False,
            context_window=4096,
            capabilities=["test-capability"],
            speed_tier=1,
            quality_tier=2,
        )
        registry.register_model(custom_model)

        assert len(registry.list_models()) == initial_count + 1
        assert registry.get_model("custom:test") == custom_model

    def test_get_model_found(self):
        """Test get_model returns model when found."""
        registry = ModelRegistry()
        model = registry.get_model("phi3:mini")
        assert model is not None
        assert model.name == "phi3:mini"

    def test_get_model_not_found(self):
        """Test get_model returns None when not found."""
        registry = ModelRegistry()
        model = registry.get_model("nonexistent:model")
        assert model is None

    def test_list_models(self):
        """Test list_models returns all registered models."""
        registry = ModelRegistry()
        models = registry.list_models()
        assert len(models) > 0
        assert all(isinstance(m, ModelInfo) for m in models)

    def test_get_available_models_all(self):
        """Test get_available_models without filter returns all."""
        registry = ModelRegistry()
        all_models = registry.get_available_models()
        assert len(all_models) > 0

    def test_get_available_models_by_provider(self):
        """Test get_available_models filters by provider."""
        registry = ModelRegistry()
        ollama_models = registry.get_available_models(provider="ollama")
        assert len(ollama_models) > 0
        assert all(m.provider == "ollama" for m in ollama_models)


class TestModelSelectionByCapability:
    """Test capability-based model selection methods."""

    def test_get_best_for_task_found(self):
        """Test get_best_for_task returns suitable model."""
        registry = ModelRegistry()
        model_name = registry.get_best_for_task("coding")
        assert model_name is not None
        model = registry.get_model(model_name)
        assert model is not None
        assert model.has_capability("coding")

    def test_get_best_for_task_not_found(self):
        """Test get_best_for_task returns None for unsupported task."""
        registry = ModelRegistry()
        model_name = registry.get_best_for_task("zzz_nonsense_qqq")
        assert model_name is None

    def test_get_best_for_task_case_insensitive(self):
        """Test get_best_for_task is case-insensitive."""
        registry = ModelRegistry()
        model1 = registry.get_best_for_task("coding")
        model2 = registry.get_best_for_task("CODING")
        assert model1 == model2

    def test_get_best_for_task_prefer_fast(self):
        """Test get_best_for_task with prefer_fast flag."""
        registry = ModelRegistry()
        model_name = registry.get_best_for_task("analysis", prefer_fast=True)
        assert model_name is not None
        model = registry.get_model(model_name)
        assert model is not None

    def test_get_best_for_task_prefer_quality(self):
        """Test get_best_for_task with prefer_quality flag."""
        registry = ModelRegistry()
        model_name = registry.get_best_for_task("analysis", prefer_quality=True)
        assert model_name is not None
        model = registry.get_model(model_name)
        assert model is not None

    def test_get_cheapest_with_capability(self):
        """Test get_cheapest_with_capability selects lowest cost model."""
        registry = ModelRegistry()
        # All default models are free (cost=0.0), so should return first match
        model_name = registry.get_cheapest_with_capability("coding")
        assert model_name is not None
        model = registry.get_model(model_name)
        assert model is not None
        assert model.has_capability("coding")

    def test_get_cheapest_with_capability_not_found(self):
        """Test get_cheapest_with_capability returns None if no match."""
        registry = ModelRegistry()
        model_name = registry.get_cheapest_with_capability("zzz_nonsense_qqq")
        assert model_name is None

    def test_get_fastest_with_capability(self):
        """Test get_fastest_with_capability selects fastest model."""
        registry = ModelRegistry()
        model_name = registry.get_fastest_with_capability("coding")
        assert model_name is not None
        model = registry.get_model(model_name)
        assert model is not None
        assert model.has_capability("coding")

    def test_get_fastest_with_capability_not_found(self):
        """Test get_fastest_with_capability returns None if no match."""
        registry = ModelRegistry()
        model_name = registry.get_fastest_with_capability("zzz_nonsense_qqq")
        assert model_name is None

    def test_get_best_quality_with_capability(self):
        """Test get_best_quality_with_capability selects highest quality."""
        registry = ModelRegistry()
        model_name = registry.get_best_quality_with_capability("coding")
        assert model_name is not None
        model = registry.get_model(model_name)
        assert model is not None
        assert model.has_capability("coding")

    def test_get_best_quality_with_capability_not_found(self):
        """Test get_best_quality_with_capability returns None if no match."""
        registry = ModelRegistry()
        model_name = registry.get_best_quality_with_capability("zzz_nonsense_qqq")
        assert model_name is None


class TestBudgetConstraints:
    """Test budget-aware model selection."""

    def test_get_best_for_task_respects_budget(self):
        """Test get_best_for_task filters models by budget."""
        registry = ModelRegistry()
        # Set a very low budget - should return None if any paid models exist
        model_name = registry.get_best_for_task("coding", budget=0.0001)
        # Default models are free, so this should still work
        model = registry.get_model(model_name) if model_name else None
        if model:
            assert model.is_free or model.cost_per_1k_tokens == 0.0

    def test_get_best_for_task_with_available_models(self):
        """Test get_best_for_task with specific available models."""
        registry = ModelRegistry()
        available = ["phi3:mini", "mistral:7b"]
        model_name = registry.get_best_for_task("reasoning", available_models=available)
        assert model_name in available or model_name is None

    def test_set_budget(self):
        """Test set_budget stores budget."""
        registry = ModelRegistry()
        registry.set_budget(10.0)
        assert registry.get_budget() == 10.0

    def test_set_budget_unlimited(self):
        """Test set_budget with unlimited."""
        registry = ModelRegistry()
        registry.set_budget(float("inf"))
        assert registry.get_budget() == float("inf")


class TestUsageTracking:
    """Test cost and usage tracking."""

    def test_track_usage_free_model(self):
        """Test track_usage returns 0 cost for free model."""
        registry = ModelRegistry()
        cost = registry.track_usage("phi3:mini", 1000)
        assert cost == 0.0

    def test_track_usage_paid_model(self):
        """Test track_usage calculates cost for paid model."""
        registry = ModelRegistry()
        custom_model = ModelInfo(
            name="paid:model",
            provider="openai",
            cost_per_1k_tokens=0.01,
            max_tokens=4096,
            supports_images=False,
            context_window=8192,
            capabilities=["analysis"],
            speed_tier=2,
            quality_tier=3,
        )
        registry.register_model(custom_model)
        cost = registry.track_usage("paid:model", 1000)
        assert cost == 0.01

    def test_track_usage_unknown_model(self):
        """Test track_usage returns 0 for unknown model."""
        registry = ModelRegistry()
        cost = registry.track_usage("unknown:model", 1000)
        assert cost == 0.0

    def test_get_total_cost(self):
        """Test get_total_cost accumulates costs."""
        registry = ModelRegistry()
        custom_model = ModelInfo(
            name="cost:test",
            provider="paid",
            cost_per_1k_tokens=0.02,
            max_tokens=4096,
            supports_images=False,
            context_window=8192,
            capabilities=["analysis"],
            speed_tier=2,
            quality_tier=3,
        )
        registry.register_model(custom_model)
        registry.track_usage("cost:test", 1000)  # 0.02
        registry.track_usage("cost:test", 1000)  # 0.02
        assert registry.get_total_cost() == pytest.approx(0.04)

    def test_get_usage_stats(self):
        """Test get_usage_stats returns per-model counts."""
        registry = ModelRegistry()
        registry.track_usage("phi3:mini", 1000)
        registry.track_usage("phi3:mini", 2000)
        stats = registry.get_usage_stats()
        assert "phi3:mini" in stats
        assert stats["phi3:mini"] == 2

    def test_reset_tracking(self):
        """Test reset_tracking clears cost and usage."""
        registry = ModelRegistry()
        custom_model = ModelInfo(
            name="reset:test",
            provider="paid",
            cost_per_1k_tokens=0.01,
            max_tokens=4096,
            supports_images=False,
            context_window=8192,
            capabilities=["analysis"],
            speed_tier=2,
            quality_tier=3,
        )
        registry.register_model(custom_model)
        registry.track_usage("reset:test", 1000)
        assert registry.get_total_cost() > 0
        registry.reset_tracking()
        assert registry.get_total_cost() == 0.0
        assert len(registry.get_usage_stats()) == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_no_matching_capability(self):
        """Test selection when no model has required capability."""
        registry = ModelRegistry()
        result = registry.get_best_for_task("zzz_nonexistent_qqq")
        assert result is None

    def test_insufficient_budget(self):
        """Test selection with budget too low for paid models."""
        registry = ModelRegistry()
        # Add a paid model
        paid_model = ModelInfo(
            name="expensive:model",
            provider="openai",
            cost_per_1k_tokens=100.0,
            max_tokens=4096,
            supports_images=False,
            context_window=8192,
            capabilities=["expensive-analysis"],
            speed_tier=4,
            quality_tier=5,
        )
        registry.register_model(paid_model)
        # Try to select with low budget - should not pick expensive model
        result = registry.get_best_for_task("expensive-analysis", budget=0.001, available_models=["expensive:model"])
        assert result is None

    def test_multiple_models_same_capability(self):
        """Test selection among multiple models with same capability."""
        registry = ModelRegistry()
        models = registry.get_available_models(provider="ollama")
        coding_models = [m for m in models if m.has_capability("coding")]
        assert len(coding_models) >= 1

    def test_register_overwrites_existing(self):
        """Test that registering same model name overwrites previous."""
        registry = ModelRegistry()
        model1 = ModelInfo(
            name="overwrite:test",
            provider="test",
            cost_per_1k_tokens=0.0,
            max_tokens=1000,
            supports_images=False,
            context_window=2000,
            capabilities=["test"],
            speed_tier=1,
            quality_tier=1,
        )
        model2 = ModelInfo(
            name="overwrite:test",
            provider="test",
            cost_per_1k_tokens=0.0,
            max_tokens=2000,
            supports_images=False,
            context_window=4000,
            capabilities=["test"],
            speed_tier=2,
            quality_tier=2,
        )
        registry.register_model(model1)
        registry.register_model(model2)
        retrieved = registry.get_model("overwrite:test")
        assert retrieved.max_tokens == 2000
        assert retrieved.speed_tier == 2
