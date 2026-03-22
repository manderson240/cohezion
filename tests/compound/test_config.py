"""Tests for compound execution configuration."""

from cohezion.compound.config import CompoundConfig


class TestCompoundConfig:
    """Test CompoundConfig model and operation routing."""

    def test_default_config(self):
        """Happy path: Create config with defaults."""
        config = CompoundConfig()

        assert config.default_model == "phi3:mini"
        assert config.code_model == "qwen3-coder:30b"
        assert config.ollama_host == "http://localhost:11434"
        assert config.cache_max_size == 512
        assert "generate" in config.operation_model_map
        assert "analyze" in config.operation_model_map

    def test_custom_config(self):
        """Happy path: Create config with custom values."""
        config = CompoundConfig(
            default_model="custom-model",
            code_model="custom-code-model",
            ollama_host="http://custom:8000",
            cache_max_size=1024,
        )

        assert config.default_model == "custom-model"
        assert config.code_model == "custom-code-model"
        assert config.ollama_host == "http://custom:8000"
        assert config.cache_max_size == 1024

    def test_model_for_operation_generate(self):
        """Integration: model_for_operation returns correct model for generate."""
        config = CompoundConfig()

        model = config.model_for_operation("generate")
        assert model == "qwen3-coder:30b"  # Should use code generation model

    def test_model_for_operation_analyze(self):
        """Integration: model_for_operation returns correct model for analyze."""
        config = CompoundConfig()

        model = config.model_for_operation("analyze")
        assert model == "phi3:mini"  # Smaller model for analysis

    def test_model_for_operation_no_llm(self):
        """Edge-empty: Operations with empty string return None (no LLM needed)."""
        config = CompoundConfig()

        model = config.model_for_operation("transform")
        assert model is None  # transform doesn't need LLM

        model = config.model_for_operation("persist")
        assert model is None  # persist doesn't need LLM

    def test_model_for_operation_unknown(self):
        """Error-case: Unknown operation uses default model."""
        config = CompoundConfig()

        model = config.model_for_operation("unknown_operation")
        assert model == "phi3:mini"  # Falls back to default_model

    def test_operation_model_map_override(self):
        """Edge-max: Custom operation model map can override defaults."""
        custom_map = {
            "generate": "custom-gen",
            "analyze": "custom-analyze",
            "search": "custom-search",
        }
        config = CompoundConfig(operation_model_map=custom_map)

        assert config.model_for_operation("generate") == "custom-gen"
        assert config.model_for_operation("analyze") == "custom-analyze"
        assert config.model_for_operation("search") == "custom-search"

    def test_empty_operation_model_map(self):
        """Edge-empty: Empty operation map falls back to default for all."""
        config = CompoundConfig(operation_model_map={})

        # All operations should use default_model
        assert config.model_for_operation("generate") == "phi3:mini"
        assert config.model_for_operation("analyze") == "phi3:mini"
        assert config.model_for_operation("search") == "phi3:mini"

    def test_model_for_operation_with_empty_string(self):
        """Edge-case: Empty string in map returns None."""
        custom_map = {"generate": ""}
        config = CompoundConfig(operation_model_map=custom_map)

        model = config.model_for_operation("generate")
        assert model is None  # Empty string → no LLM

    def test_config_serialization(self):
        """Integration: Config can be serialized to dict."""
        config = CompoundConfig()
        data = config.model_dump()

        assert "default_model" in data
        assert "code_model" in data
        assert "operation_model_map" in data
        assert data["ollama_host"] == "http://localhost:11434"
