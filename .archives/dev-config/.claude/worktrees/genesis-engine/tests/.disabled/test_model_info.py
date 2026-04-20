"""Unit tests for ModelInfo dataclass.

Tests validation, serialization, and capability checking.
"""

import pytest

from cohezion.models.model_info import ModelInfo


class TestModelInfoValidation:
    """Test ModelInfo validation in __post_init__."""

    def test_valid_tiers(self):
        """Test that valid tier values (1-5) are accepted."""
        model = ModelInfo(
            name="test-model",
            provider="ollama",
            cost_per_1k_tokens=0.0,
            max_tokens=4096,
            supports_images=False,
            context_window=8192,
            capabilities=["analysis"],
            speed_tier=1,
            quality_tier=5,
        )
        assert model.speed_tier == 1
        assert model.quality_tier == 5

    def test_invalid_speed_tier_too_low(self):
        """Test that speed_tier < 1 raises ValueError."""
        with pytest.raises(ValueError, match="speed_tier must be 1-5"):
            ModelInfo(
                name="test-model",
                provider="ollama",
                cost_per_1k_tokens=0.0,
                max_tokens=4096,
                supports_images=False,
                context_window=8192,
                capabilities=["analysis"],
                speed_tier=0,
                quality_tier=3,
            )

    def test_invalid_speed_tier_too_high(self):
        """Test that speed_tier > 5 raises ValueError."""
        with pytest.raises(ValueError, match="speed_tier must be 1-5"):
            ModelInfo(
                name="test-model",
                provider="ollama",
                cost_per_1k_tokens=0.0,
                max_tokens=4096,
                supports_images=False,
                context_window=8192,
                capabilities=["analysis"],
                speed_tier=6,
                quality_tier=3,
            )

    def test_invalid_quality_tier_too_low(self):
        """Test that quality_tier < 1 raises ValueError."""
        with pytest.raises(ValueError, match="quality_tier must be 1-5"):
            ModelInfo(
                name="test-model",
                provider="ollama",
                cost_per_1k_tokens=0.0,
                max_tokens=4096,
                supports_images=False,
                context_window=8192,
                capabilities=["analysis"],
                speed_tier=3,
                quality_tier=0,
            )

    def test_invalid_quality_tier_too_high(self):
        """Test that quality_tier > 5 raises ValueError."""
        with pytest.raises(ValueError, match="quality_tier must be 1-5"):
            ModelInfo(
                name="test-model",
                provider="ollama",
                cost_per_1k_tokens=0.0,
                max_tokens=4096,
                supports_images=False,
                context_window=8192,
                capabilities=["analysis"],
                speed_tier=3,
                quality_tier=6,
            )


class TestModelInfoCapabilities:
    """Test capability checking methods."""

    def test_has_capability_exact_match(self):
        """Test has_capability with exact match."""
        model = ModelInfo(
            name="test-model",
            provider="ollama",
            cost_per_1k_tokens=0.0,
            max_tokens=4096,
            supports_images=False,
            context_window=8192,
            capabilities=["analysis", "coding", "synthesis"],
            speed_tier=2,
            quality_tier=3,
        )
        assert model.has_capability("analysis") is True
        assert model.has_capability("coding") is True

    def test_has_capability_case_insensitive(self):
        """Test has_capability is case-insensitive."""
        model = ModelInfo(
            name="test-model",
            provider="ollama",
            cost_per_1k_tokens=0.0,
            max_tokens=4096,
            supports_images=False,
            context_window=8192,
            capabilities=["Analysis", "CODING"],
            speed_tier=2,
            quality_tier=3,
        )
        assert model.has_capability("analysis") is True
        assert model.has_capability("ANALYSIS") is True
        assert model.has_capability("coding") is True
        assert model.has_capability("CODING") is True

    def test_has_capability_missing(self):
        """Test has_capability returns False for missing capability."""
        model = ModelInfo(
            name="test-model",
            provider="ollama",
            cost_per_1k_tokens=0.0,
            max_tokens=4096,
            supports_images=False,
            context_window=8192,
            capabilities=["analysis"],
            speed_tier=2,
            quality_tier=3,
        )
        assert model.has_capability("vision") is False
        assert model.has_capability("coding") is False


class TestModelInfoProperties:
    """Test computed properties."""

    def test_is_local_true_for_ollama(self):
        """Test is_local returns True for ollama provider."""
        model = ModelInfo(
            name="test-model",
            provider="ollama",
            cost_per_1k_tokens=0.0,
            max_tokens=4096,
            supports_images=False,
            context_window=8192,
            capabilities=["analysis"],
            speed_tier=2,
            quality_tier=3,
        )
        assert model.is_local is True

    def test_is_local_false_for_other_providers(self):
        """Test is_local returns False for non-ollama providers."""
        model = ModelInfo(
            name="gpt-4",
            provider="openai",
            cost_per_1k_tokens=0.03,
            max_tokens=8192,
            supports_images=True,
            context_window=128000,
            capabilities=["analysis", "coding"],
            speed_tier=4,
            quality_tier=5,
        )
        assert model.is_local is False

    def test_is_free_true_for_zero_cost(self):
        """Test is_free returns True when cost is 0.0."""
        model = ModelInfo(
            name="test-model",
            provider="ollama",
            cost_per_1k_tokens=0.0,
            max_tokens=4096,
            supports_images=False,
            context_window=8192,
            capabilities=["analysis"],
            speed_tier=2,
            quality_tier=3,
        )
        assert model.is_free is True

    def test_is_free_false_for_nonzero_cost(self):
        """Test is_free returns False when cost > 0."""
        model = ModelInfo(
            name="gpt-4",
            provider="openai",
            cost_per_1k_tokens=0.03,
            max_tokens=8192,
            supports_images=True,
            context_window=128000,
            capabilities=["analysis"],
            speed_tier=4,
            quality_tier=5,
        )
        assert model.is_free is False


class TestModelInfoSerialization:
    """Test to_dict and from_dict serialization round-trip."""

    def test_to_dict(self):
        """Test to_dict converts ModelInfo to dictionary."""
        model = ModelInfo(
            name="test-model",
            provider="ollama",
            cost_per_1k_tokens=0.0,
            max_tokens=4096,
            supports_images=False,
            context_window=8192,
            capabilities=["analysis", "coding"],
            speed_tier=2,
            quality_tier=3,
            metadata={"variant": "7b"},
        )
        result = model.to_dict()
        assert result["name"] == "test-model"
        assert result["provider"] == "ollama"
        assert result["cost_per_1k_tokens"] == 0.0
        assert result["max_tokens"] == 4096
        assert result["supports_images"] is False
        assert result["context_window"] == 8192
        assert result["capabilities"] == ["analysis", "coding"]
        assert result["speed_tier"] == 2
        assert result["quality_tier"] == 3
        assert result["metadata"] == {"variant": "7b"}

    def test_from_dict(self):
        """Test from_dict creates ModelInfo from dictionary."""
        data = {
            "name": "test-model",
            "provider": "ollama",
            "cost_per_1k_tokens": 0.0,
            "max_tokens": 4096,
            "supports_images": False,
            "context_window": 8192,
            "capabilities": ["analysis", "coding"],
            "speed_tier": 2,
            "quality_tier": 3,
            "metadata": {"variant": "7b"},
        }
        model = ModelInfo.from_dict(data)
        assert model.name == "test-model"
        assert model.provider == "ollama"
        assert model.cost_per_1k_tokens == 0.0
        assert model.max_tokens == 4096
        assert model.supports_images is False
        assert model.context_window == 8192
        assert model.capabilities == ["analysis", "coding"]
        assert model.speed_tier == 2
        assert model.quality_tier == 3
        assert model.metadata == {"variant": "7b"}

    def test_serialization_round_trip(self):
        """Test that to_dict/from_dict round-trip preserves data."""
        original = ModelInfo(
            name="mistral:7b",
            provider="ollama",
            cost_per_1k_tokens=0.0,
            max_tokens=8192,
            supports_images=False,
            context_window=32768,
            capabilities=["analysis", "synthesis", "coding"],
            speed_tier=3,
            quality_tier=3,
            metadata={"variant": "7b", "architecture": "mistral"},
        )
        serialized = original.to_dict()
        restored = ModelInfo.from_dict(serialized)

        assert restored.name == original.name
        assert restored.provider == original.provider
        assert restored.cost_per_1k_tokens == original.cost_per_1k_tokens
        assert restored.max_tokens == original.max_tokens
        assert restored.supports_images == original.supports_images
        assert restored.context_window == original.context_window
        assert restored.capabilities == original.capabilities
        assert restored.speed_tier == original.speed_tier
        assert restored.quality_tier == original.quality_tier
        assert restored.metadata == original.metadata

    def test_from_dict_without_metadata(self):
        """Test from_dict handles missing metadata field."""
        data = {
            "name": "test-model",
            "provider": "ollama",
            "cost_per_1k_tokens": 0.0,
            "max_tokens": 4096,
            "supports_images": False,
            "context_window": 8192,
            "capabilities": ["analysis"],
            "speed_tier": 2,
            "quality_tier": 3,
        }
        model = ModelInfo.from_dict(data)
        assert model.metadata == {}
