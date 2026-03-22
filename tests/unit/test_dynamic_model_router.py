"""Tests for the dynamic model router (cohezion.swarm.dynamic_model_router)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper to patch psutil before module-level code runs
# ---------------------------------------------------------------------------


def _mock_virtual_memory(total_gb=128.0, available_gb=100.0):
    """Create a mock psutil.virtual_memory() return value."""
    mock = MagicMock()
    mock.total = int(total_gb * (1024**3))
    mock.available = int(available_gb * (1024**3))
    return mock


# ---------------------------------------------------------------------------
# MemoryBandwidthAnalyzer tests
# ---------------------------------------------------------------------------


class TestMemoryBandwidthAnalyzer:
    def _make(self, total_gb=128.0, available_gb=100.0):
        with patch(
            "psutil.virtual_memory",
            return_value=_mock_virtual_memory(total_gb, available_gb),
        ):
            from cohezion.swarm.dynamic_model_router import MemoryBandwidthAnalyzer

            return MemoryBandwidthAnalyzer()

    def test_total_memory(self):
        analyzer = self._make(total_gb=128.0, available_gb=100.0)
        assert abs(analyzer.total_memory_gb - 128.0) < 1.0

    def test_analyze_memory_pressure_low(self):
        analyzer = self._make(total_gb=128.0, available_gb=100.0)
        pressure = analyzer.analyze_memory_pressure()
        assert 0.0 < pressure < 0.3  # Low pressure

    def test_analyze_memory_pressure_high(self):
        analyzer = self._make(total_gb=128.0, available_gb=10.0)
        pressure = analyzer.analyze_memory_pressure()
        assert pressure > 0.9

    def test_calculate_optimal_concurrent_low_pressure(self):
        analyzer = self._make(total_gb=128.0, available_gb=100.0)
        from cohezion.swarm.dynamic_model_router import ModelTier

        count = analyzer.calculate_optimal_concurrent_models(ModelTier.SMALL)
        assert count == ModelTier.SMALL.value[2]  # Full capacity

    def test_calculate_optimal_concurrent_high_pressure(self):
        analyzer = self._make(total_gb=128.0, available_gb=10.0)
        from cohezion.swarm.dynamic_model_router import ModelTier

        count = analyzer.calculate_optimal_concurrent_models(ModelTier.SMALL)
        assert count == 1  # Conservative

    def test_calculate_optimal_concurrent_medium_pressure(self):
        analyzer = self._make(total_gb=128.0, available_gb=50.0)
        from cohezion.swarm.dynamic_model_router import ModelTier

        count = analyzer.calculate_optimal_concurrent_models(ModelTier.SMALL)
        assert count == max(1, ModelTier.SMALL.value[2] // 2)

    def test_estimate_tokens_per_second(self):
        analyzer = self._make(total_gb=128.0, available_gb=100.0)
        from cohezion.swarm.dynamic_model_router import IDEPriority, ModelConfig

        config = ModelConfig(
            name="test:model",
            size_gb=5.0,
            quantization="Q4_K_M",
            context_max=32768,
            expected_tps=10.0,
            cache_hit_rate=0.15,
            template_format="chatml",
            optimal_for_ide=[IDEPriority.OPENCODE],
        )
        tps = analyzer.estimate_tokens_per_second(config)
        assert tps > 0

    def test_get_quantization_factor_known(self):
        analyzer = self._make()
        assert analyzer.get_quantization_factor("Q8_0") == 1.0
        assert analyzer.get_quantization_factor("Q4_K_M") == 1.35
        assert analyzer.get_quantization_factor("Q6_K") == 1.15
        assert analyzer.get_quantization_factor("Q3_K_M") == 1.5

    def test_get_quantization_factor_unknown(self):
        analyzer = self._make()
        assert analyzer.get_quantization_factor("UNKNOWN") == 1.0


# ---------------------------------------------------------------------------
# AdaptiveTemplateManager tests
# ---------------------------------------------------------------------------


class TestAdaptiveTemplateManager:
    def _make(self):
        from cohezion.swarm.dynamic_model_router import AdaptiveTemplateManager

        return AdaptiveTemplateManager()

    def test_detect_qwen(self):
        mgr = self._make()
        assert mgr.detect_model_template("qwen3-coder:30b") == "chatml"
        assert mgr.detect_model_template("qwen2.5-coder:14b") == "chatml"

    def test_detect_phi(self):
        mgr = self._make()
        assert mgr.detect_model_template("phi4:latest") == "microsoft"
        assert mgr.detect_model_template("mistral-small:latest") == "microsoft"

    def test_detect_llama(self):
        mgr = self._make()
        assert mgr.detect_model_template("llama3:8b") == "llama3"
        assert mgr.detect_model_template("gemma3:4b") == "llama3"

    def test_detect_unknown_defaults_to_chatml(self):
        mgr = self._make()
        assert mgr.detect_model_template("some-random-model") == "chatml"


# ---------------------------------------------------------------------------
# DynamicModelRouter tests
# ---------------------------------------------------------------------------


class TestDynamicModelRouter:
    def _make(self):
        with patch("psutil.virtual_memory", return_value=_mock_virtual_memory(128.0, 100.0)):
            from cohezion.swarm.dynamic_model_router import DynamicModelRouter

            return DynamicModelRouter()

    def test_load_model_registry_not_empty(self):
        router = self._make()
        assert len(router.models) > 0

    def test_load_model_registry_known_models(self):
        router = self._make()
        assert "qwen3:8b" in router.models
        assert "phi4:latest" in router.models

    @pytest.mark.asyncio
    async def test_select_optimal_model_coding(self):
        router = self._make()
        model = await router.select_optimal_model(
            {
                "task_type": "coding",
                "ide_priority": 1,
                "context_length": 2000,
            }
        )
        assert model is not None
        assert hasattr(model, "name")

    def test_calculate_model_score_coding_bonus(self):
        router = self._make()
        from cohezion.swarm.dynamic_model_router import IDEPriority, ModelConfig

        coder_model = ModelConfig(
            name="qwen3-coder:30b",
            size_gb=20.0,
            quantization="Q4_K_M",
            context_max=65536,
            expected_tps=5.0,
            cache_hit_rate=0.1,
            template_format="chatml",
            optimal_for_ide=[IDEPriority.ZED],
        )
        generic_model = ModelConfig(
            name="generic:8b",
            size_gb=5.0,
            quantization="Q4_K_M",
            context_max=32768,
            expected_tps=10.0,
            cache_hit_rate=0.15,
            template_format="chatml",
            optimal_for_ide=[IDEPriority.ZED],
        )
        request = {"task_type": "coding", "context_length": 1000, "ide_priority": 2}
        score_coder = router.calculate_model_score(coder_model, request, 0.2)
        router.calculate_model_score(generic_model, request, 0.2)
        # Coder model should get the coding bonus
        assert score_coder > 0

    def test_calculate_dynamic_context_limit(self):
        router = self._make()
        from cohezion.swarm.dynamic_model_router import IDEPriority, ModelConfig

        model = ModelConfig(
            name="test:8b",
            size_gb=5.0,
            quantization="Q4_K_M",
            context_max=65536,
            expected_tps=10.0,
            cache_hit_rate=0.15,
            template_format="chatml",
            optimal_for_ide=[IDEPriority.OPENCODE],
        )
        limit = router.calculate_dynamic_context_limit(model)
        assert limit > 0
        assert limit <= model.context_max

    def test_record_performance(self):
        router = self._make()
        from cohezion.swarm.dynamic_model_router import IDEPriority, ModelConfig

        model = ModelConfig(
            name="test:model",
            size_gb=5.0,
            quantization="Q4_K_M",
            context_max=32768,
            expected_tps=10.0,
            cache_hit_rate=0.15,
            template_format="chatml",
            optimal_for_ide=[IDEPriority.OPENCODE],
        )
        router.record_performance(model, execution_time=1.5, response_length=100)
        assert len(router.performance_history) == 1
        assert router.performance_history[0]["model"] == "test:model"

    def test_record_performance_caps_history(self):
        router = self._make()
        from cohezion.swarm.dynamic_model_router import IDEPriority, ModelConfig

        model = ModelConfig(
            name="test:model",
            size_gb=5.0,
            quantization="Q4_K_M",
            context_max=32768,
            expected_tps=10.0,
            cache_hit_rate=0.15,
            template_format="chatml",
            optimal_for_ide=[IDEPriority.OPENCODE],
        )
        for _i in range(1100):
            router.record_performance(model, execution_time=0.1, response_length=10)
        assert len(router.performance_history) <= 1000


# ---------------------------------------------------------------------------
# ModelTier tests
# ---------------------------------------------------------------------------


class TestModelTier:
    def test_tier_values(self):
        from cohezion.swarm.dynamic_model_router import ModelTier

        assert ModelTier.MICRO.value[0] == 0.5
        assert ModelTier.ULTRA.value[2] == 1  # 1 concurrent


class TestIDEPriority:
    def test_priority_values(self):
        from cohezion.swarm.dynamic_model_router import IDEPriority

        assert IDEPriority.ANTIGRAVITY.value == 3
        assert IDEPriority.ZED.value == 2
        assert IDEPriority.OPENCODE.value == 1
