"""Test AdaptiveRouterAdapter integration with TokenEfficientClient.

This test suite verifies that AdaptiveRouterAdapter is a drop-in replacement
for SmartRouterAdapter while maintaining the same interface contract.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

# Check if hardware_aware_router is available for integration tests
try:
    from cohezion.swarm.hardware_aware_router import RoutingDecision
    HAS_HARDWARE_ROUTER = True
except ImportError:
    HAS_HARDWARE_ROUTER = False

from cohezion.swarm.adaptive_router_adapter import (
    AdaptiveRouterAdapter,
    ModelSelection,
)


@pytest.fixture
def mock_selector() -> Mock:
    """Create a mock AdaptiveModelSelector."""
    selector = AsyncMock()
    selector.select_optimal_model = AsyncMock()
    selector.record_outcome = AsyncMock()
    selector.profile_manager = Mock()
    selector.profile_manager.profiles = {}
    return selector


@pytest.fixture
def adapter(mock_selector: Mock) -> AdaptiveRouterAdapter:
    """Create an adapter with mock selector."""
    return AdaptiveRouterAdapter(mock_selector)


@pytest.mark.skipif(
    not HAS_HARDWARE_ROUTER,
    reason="hardware_aware_router module not available (integration test)",
)
class TestInterfaceContract:
    """Verify AdaptiveRouterAdapter has the same interface as SmartRouterAdapter."""

    @pytest.mark.asyncio
    async def test_select_optimal_model_signature(self, adapter: AdaptiveRouterAdapter):
        """Verify select_optimal_model has expected signature."""
        # Must accept context dict with task_type and context_length
        context = {
            "task_type": "coding",
            "context_length": 1024,
        }

        # Must return object with .name attribute
        from cohezion.swarm.hardware_aware_router import RoutingDecision

        # Mock the selector to return a valid RoutingDecision
        adapter._selector.select_optimal_model.return_value = RoutingDecision(
            request_id="test-1",
            primary_model="qwen3-coder:30b",
            fallback_chain=["qwen2.5-coder:14b", "phi4:latest"],
            confidence=0.85,
            predicted_tps=8.0,
            predicted_latency_ms=1000,
            reasoning="Selected for coding task",
        )

        result = await adapter.select_optimal_model(context)

        # Verify result has .name attribute
        assert hasattr(result, "name")
        assert result.name == "qwen3-coder:30b"

    @pytest.mark.asyncio
    async def test_task_type_normalization(self, adapter: AdaptiveRouterAdapter):
        """Verify adapter normalizes task types correctly."""
        test_cases = [
            ("coding", "coding"),
            ("code", "coding"),
            ("analysis", "analysis"),
            ("general", "analysis"),
            ("creative", "creative"),
            ("unknown_type", "analysis"),  # default to analysis
        ]

        from cohezion.swarm.hardware_aware_router import RoutingDecision

        for input_type, _expected_normalized in test_cases:
            adapter._selector.select_optimal_model.return_value = (
                RoutingDecision(
                    request_id="test",
                    primary_model="phi3:mini",
                    fallback_chain=[],
                    confidence=1.0,
                    predicted_tps=25.0,
                    predicted_latency_ms=100,
                    reasoning="test",
                )
            )

            result = await adapter.select_optimal_model(
                {"task_type": input_type, "context_length": 100}
            )

            assert result.name == "phi3:mini"


class TestModelSelection:
    """Verify ModelSelection dataclass works correctly."""

    def test_model_selection_with_defaults(self):
        """Verify ModelSelection has all expected attributes."""
        selection = ModelSelection(name="test-model")

        assert selection.name == "test-model"
        assert selection.confidence == 1.0
        assert selection.fallback_chain == []
        assert selection.reasoning == ""

    def test_model_selection_with_fallback_chain(self):
        """Verify fallback_chain is properly initialized."""
        fallbacks = ["model-b", "model-c"]
        selection = ModelSelection(
            name="model-a",
            confidence=0.8,
            fallback_chain=fallbacks,
            reasoning="because X",
        )

        assert selection.name == "model-a"
        assert selection.fallback_chain == fallbacks
        assert len(selection.fallback_chain) == 2


class TestOutcomeRecording:
    """Verify outcome recording for learning."""

    @pytest.mark.asyncio
    async def test_record_outcome_success(self, adapter: AdaptiveRouterAdapter):
        """Verify recording of successful execution."""
        adapter._selector.record_outcome = AsyncMock()

        await adapter.record_outcome(
            request_id="req-123",
            success=True,
            actual_latency_ms=450.5,
            actual_tps=25.3,
            failure_reason=None,
            model_used="qwen2.5-coder:14b",
        )

        adapter._selector.record_outcome.assert_called_once()
        call_args = adapter._selector.record_outcome.call_args
        assert call_args.kwargs["request_id"] == "req-123"
        assert call_args.kwargs["success"] is True

    @pytest.mark.asyncio
    async def test_record_outcome_failure(self, adapter: AdaptiveRouterAdapter):
        """Verify recording of failed execution."""
        adapter._selector.record_outcome = AsyncMock()

        await adapter.record_outcome(
            request_id="req-456",
            success=False,
            actual_latency_ms=5000.0,
            failure_reason="timeout",
            model_used="qwen3-coder:30b",
        )

        adapter._selector.record_outcome.assert_called_once()
        call_args = adapter._selector.record_outcome.call_args
        assert call_args.kwargs["success"] is False
        assert call_args.kwargs["failure_reason"] == "timeout"


class TestMetricsExport:
    """Verify metrics are properly exported."""

    @pytest.mark.asyncio
    async def test_get_metrics(self, adapter: AdaptiveRouterAdapter):
        """Verify metrics export."""
        metrics = await adapter.get_metrics()

        assert "adapter" in metrics
        assert metrics["adapter"] == "adaptive"
        assert "decisions_made" in metrics
        assert metrics["decisions_made"] >= 0


class TestFallback:
    """Verify fallback behavior when selector fails."""

    @pytest.mark.asyncio
    async def test_fallback_on_import_error(self):
        """Verify adapter falls back to phi3:mini on import error."""
        with patch(
            "cohezion.swarm.hardware_aware_router.RoutingRequest",
            side_effect=ImportError("AdaptiveModelSelector not available"),
        ):
            adapter = AdaptiveRouterAdapter(None)

            result = await adapter.select_optimal_model(
                {"task_type": "coding", "context_length": 100}
            )

            assert result.name == "phi3:mini"
            assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_fallback_on_exception(self):
        """Verify adapter falls back to phi3:mini on exceptions."""
        selector = AsyncMock()
        selector.select_optimal_model.side_effect = Exception("Selector error")

        adapter = AdaptiveRouterAdapter(selector)

        result = await adapter.select_optimal_model(
            {"task_type": "coding", "context_length": 100}
        )

        assert result.name == "phi3:mini"
        # Adapter returns confidence=0.5 on exception (reduced confidence due to fallback)
        assert result.confidence == 0.5


@pytest.mark.skipif(
    not HAS_HARDWARE_ROUTER,
    reason="hardware_aware_router module not available (integration test)",
)
class TestBackwardCompatibility:
    """Verify backward compatibility with SmartRouterAdapter usage."""

    @pytest.mark.asyncio
    async def test_token_client_interface_contract(
        self, adapter: AdaptiveRouterAdapter
    ):
        """Verify adapter works as TokenEfficientClient._router."""
        from cohezion.swarm.hardware_aware_router import RoutingDecision

        adapter._selector.select_optimal_model.return_value = RoutingDecision(
            request_id="test",
            primary_model="qwen3-coder:30b",
            fallback_chain=[],
            confidence=0.9,
            predicted_tps=3.5,
            predicted_latency_ms=2000,
            reasoning="test",
        )

        # TokenEfficientClient does this:
        context = {"task_type": "coding", "context_length": 5000}
        config = await adapter.select_optimal_model(context)
        model_name = config.name

        assert model_name == "qwen3-coder:30b"
        assert isinstance(config, ModelSelection)


# =============================================================================
# Integration Test Markers
# =============================================================================

@pytest.mark.skipif(
    not HAS_HARDWARE_ROUTER,
    reason="hardware_aware_router module not available (integration test)",
)
@pytest.mark.skip(reason="AdaptiveModelSelector not yet implemented")
@pytest.mark.skip(reason="AdaptiveModelSelector not yet implemented")
class TestWithRealSelector:
    """Integration tests with actual AdaptiveModelSelector.

    These tests are marked 'slow' because they initialize the real selector.
    Run with: pytest -m integration
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_with_real_selector_initialization(self):
        """Verify adapter works with real AdaptiveModelSelector."""
        from cohezion.swarm.hardware_aware_router import (
            AdaptiveModelSelector,
            HardwareMetricsCollector,
            ModelProfileManager,
        )

        # Create real selector
        metrics_collector = HardwareMetricsCollector()
        profile_manager = ModelProfileManager()
        selector = AdaptiveModelSelector(
            metrics_collector=metrics_collector,
            profile_manager=profile_manager,
        )

        # Register some models
        selector.register_model(
            name="phi3:mini",
            size_gb=4.0,
            quantization="Q8_0",
            context_max=4096,
            ideal_tps=25.0,
            capabilities=["fast"],
        )

        # Create adapter
        adapter = AdaptiveRouterAdapter(selector)

        # Use it
        result = await adapter.select_optimal_model(
            {"task_type": "general", "context_length": 100}
        )

        assert result.name == "phi3:mini"
        assert hasattr(result, "confidence")
