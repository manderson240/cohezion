"""Tests for compound_client, model_adapter, and API wiring.

All Ollama HTTP calls are mocked — no real Ollama is needed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.swarm.compound_client import (
    create_compound_client,
    get_compound_client,
    reset_compound_client,
)
from cohezion.swarm.model_adapter import _TASK_TYPE_MAP, SmartRouterAdapter
from cohezion.swarm.smart_router import LOCAL_MODELS, SmartRouter
from cohezion.swarm.token_client import TokenEfficientClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Ensure the compound client singleton is reset between tests."""
    reset_compound_client()
    yield
    reset_compound_client()


# ---------------------------------------------------------------------------
# test_create_compound_client
# ---------------------------------------------------------------------------


def test_create_compound_client():
    """create_compound_client returns a configured TokenEfficientClient."""
    client = create_compound_client()

    assert isinstance(client, TokenEfficientClient)
    # Router is a SmartRouterAdapter
    assert isinstance(client.router, SmartRouterAdapter)
    # Ollama client is set
    assert client.ollama is not None
    # Cache is empty initially (accessed via property)
    assert len(client._cache) == 0


# ---------------------------------------------------------------------------
# test_singleton_returns_same_instance
# ---------------------------------------------------------------------------


def test_singleton_returns_same_instance():
    """get_compound_client returns the same instance on repeated calls."""
    a = get_compound_client()
    b = get_compound_client()
    assert a is b


# ---------------------------------------------------------------------------
# test_smart_router_adapter_maps_task_types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_smart_router_adapter_maps_task_types():
    """SmartRouterAdapter maps string task_types to SmartRouter TaskType enums."""
    router = SmartRouter(strategy="efficiency")
    # Seed available models so route() has something to score
    router.available_models = dict(LOCAL_MODELS)

    adapter = SmartRouterAdapter(router)

    for task_str, _expected_enum in _TASK_TYPE_MAP.items():
        result = await adapter.select_optimal_model({"task_type": task_str, "context_length": 100})
        assert hasattr(result, "name")
        assert isinstance(result.name, str)
        assert len(result.name) > 0


# ---------------------------------------------------------------------------
# test_adapter_fallback_on_error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adapter_fallback_on_error():
    """SmartRouterAdapter still returns a model even when refresh_models fails."""
    router = SmartRouter(strategy="efficiency")
    # Force refresh_models to raise
    router.refresh_models = AsyncMock(side_effect=RuntimeError("no ollama"))
    # No available models pre-seeded
    router.available_models = {}

    adapter = SmartRouterAdapter(router)

    result = await adapter.select_optimal_model({"task_type": "coding", "context_length": 50})
    # Should fall through to SmartRouter.route()'s ultimate fallback
    assert hasattr(result, "name")
    assert isinstance(result.name, str)


# ---------------------------------------------------------------------------
# test_compound_client_caches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compound_client_caches():
    """Compound client caches identical prompts (mock Ollama)."""
    client = create_compound_client()

    # Mock the underlying Ollama client's generate method
    # Note: generate() returns (response_text, token_count)
    mock_response = ("This is a test response", 42)
    client.ollama = AsyncMock()
    client.ollama.generate = AsyncMock(return_value=mock_response)

    # First call: cache miss
    result1, _tokens1 = await client.generate("test prompt", system="sys", model="phi3:mini")
    assert result1 == "This is a test response"
    # Check metrics via get_metrics()
    metrics = client.get_metrics()
    assert metrics["cache_misses"] == 1
    assert metrics["total_cache_hits"] == 0

    # Second call: cache hit (same prompt + system + model)
    result2, _tokens2 = await client.generate("test prompt", system="sys", model="phi3:mini")
    assert result2 == "This is a test response"
    metrics = client.get_metrics()
    assert metrics["total_cache_hits"] == 1

    # Ollama should have been called only once
    assert client.ollama.generate.call_count == 1


# ---------------------------------------------------------------------------
# test_compound_client_metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compound_client_metrics():
    """Verify metrics track after multiple calls."""
    client = create_compound_client()

    client.ollama = AsyncMock()
    client.ollama.generate = AsyncMock(return_value=("response A", 50))

    _, _ = await client.generate("prompt A", model="phi3:mini")
    _, _ = await client.generate("prompt B", model="phi3:mini")
    _, _ = await client.generate("prompt A", model="phi3:mini")  # cache hit

    metrics = client.get_metrics()
    # Verify metrics track cache operations correctly
    assert "total_cache_hits" in metrics
    assert "cache_misses" in metrics
    assert metrics["total_cache_hits"] == 1
    assert metrics["cache_misses"] == 2
    assert metrics["combined_hit_rate"] > 0


# ---------------------------------------------------------------------------
# test_api_swarm_execute_uses_compound_client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_swarm_execute_uses_compound_client():
    """The /swarm/execute endpoint uses the compound client."""
    from fastapi.testclient import TestClient

    from cohezion.api import app

    with (
        patch("cohezion.swarm.compound_client.get_compound_client") as mock_get_cc,
        patch("cohezion.swarm.team_orchestrator.TeamOrchestrator") as mock_orch_cls,
        patch("cohezion.swarm.execution_orchestrator.ExecutionOrchestrator") as mock_exec_cls,
    ):
        mock_client = MagicMock()
        mock_get_cc.return_value = mock_client

        # TeamOrchestrator.plan_team returns a minimal plan
        mock_plan = MagicMock()
        mock_orch_instance = MagicMock()
        mock_orch_instance.plan_team.return_value = mock_plan
        mock_orch_cls.return_value = mock_orch_instance

        # ExecutionOrchestrator.execute returns a minimal report
        mock_report = MagicMock()
        mock_report.to_dict.return_value = {
            "report_id": "test_123",
            "plan_name": "test-plan",
            "intent": "test",
            "status": "completed",
            "total_tokens": 10,
            "total_duration_ms": 50.0,
            "tasks": [],
        }
        mock_exec_instance = MagicMock()
        mock_exec_instance.execute = AsyncMock(return_value=mock_report)
        mock_exec_cls.return_value = mock_exec_instance

        client = TestClient(app)
        resp = client.post(
            "/swarm/execute",
            json={"intent": "test the system", "max_agents": 2},
        )
        assert resp.status_code == 200

        # Verify compound client was fetched
        mock_get_cc.assert_called_once()
        # Verify ExecutionOrchestrator was created with compound client
        mock_exec_cls.assert_called_once_with(token_client=mock_client)


# ---------------------------------------------------------------------------
# test_api_skill_execute_uses_compound_client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_skill_execute_uses_compound_client():
    """The /skills/{name}/execute endpoint uses the compound client."""
    from fastapi.testclient import TestClient

    from cohezion.api import app
    from cohezion.core.instruction_expander import ExecutablePlan, PlanStep
    from cohezion.core.plan_executor import ExecutionResult, StepResult

    mock_spec = MagicMock()
    mock_spec.name = "test_skill"

    mock_plan = ExecutablePlan(
        skill_name="test_skill",
        domain="testing",
        steps=[PlanStep(operation="analyze", description="analyze input")],
    )

    mock_exec_result = ExecutionResult(
        skill_name="test_skill",
        steps=[
            StepResult(
                step_index=0,
                operation="analyze",
                output="analyzed",
                tokens_used=5,
                duration_ms=10.0,
            )
        ],
        final_output="analyzed",
        total_tokens=5,
        total_duration_ms=10.0,
    )

    with (
        patch("cohezion.swarm.compound_client.get_compound_client") as mock_get_cc,
        patch("cohezion.agents.factory.AgentFactory") as mock_factory_cls,
        patch("cohezion.core.instruction_expander.InstructionExpander") as mock_expander_cls,
        patch("cohezion.core.plan_executor.PlanExecutor") as mock_executor_cls,
    ):
        mock_client = MagicMock()
        mock_get_cc.return_value = mock_client

        mock_factory = MagicMock()
        mock_factory._resolve_spec.return_value = mock_spec
        mock_factory_cls.return_value = mock_factory

        mock_expander = MagicMock()
        mock_expander.expand.return_value = mock_plan
        mock_expander_cls.return_value = mock_expander

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(return_value=mock_exec_result)
        mock_executor_cls.return_value = mock_executor

        client = TestClient(app)
        resp = client.post(
            "/skills/test_skill/execute",
            json={"input_text": "hello world"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill_name"] == "test_skill"
        assert data["status"] == "executed"

        # Verify compound client was passed to PlanExecutor
        mock_get_cc.assert_called_once()
        mock_executor_cls.assert_called_once_with(token_client=mock_client)
