"""Shared test fixtures for the Cohezion test suite."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_ollama():
    """Patch httpx calls to Ollama, returning a canned JSON response."""
    canned = {"response": "mocked-ollama-response", "done": True}
    mock_response = MagicMock(
        status_code=200,
        json=MagicMock(return_value=canned),
        raise_for_status=MagicMock(),
    )
    with patch(
        "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response
    ) as mock_post:
        yield mock_post


@pytest.fixture
def mock_surreal():
    """Patch SurrealDB client methods to return empty results without a live connection."""
    with patch("cohezion.core.persistence.surreal_client.SurrealClient") as mock_cls:
        instance = mock_cls.return_value
        instance.connect = AsyncMock()
        instance.close = AsyncMock()
        instance.query = AsyncMock(return_value=[])
        instance.store_node = AsyncMock()
        instance.get_node = AsyncMock(return_value=None)
        yield instance


@pytest.fixture
def tmp_workdir(tmp_path: Path):
    """Provide a temporary working directory that auto-cleans after the test."""
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    return workdir


@pytest.fixture(autouse=True)
def event_loop_fixture():
    """Ensure a fresh event loop is available for each test."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()
    else:
        # Already have a running loop (pytest-asyncio)
        yield


@pytest.fixture(autouse=True)
def reset_singletons():
    """Auto-reset critical singletons before each test to prevent state pollution."""
    import logging
    from cohezion.compound.executor import ExecutorFactory
    from cohezion.compound.batch_executor import BatchableExecutor
    from cohezion.swarm.cost_aware_router import CostAwareRouter
    from cohezion.cost_optimization.cost_tracker import SessionCostTracker
    from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer
    from cohezion.concurrency.ollama_gate import reset_gate
    from cohezion.swarm.model_pool_manager import reset_pool_manager

    # Reset before test
    reset_gate()  # Reset OllamaGate singleton
    reset_pool_manager()  # Reset ModelPoolManager singleton
    ExecutorFactory.reset_singleton()
    if hasattr(BatchableExecutor, "reset_singleton"):
        BatchableExecutor.reset_singleton()
    if hasattr(CostAwareRouter, "reset_singleton"):
        CostAwareRouter.reset_singleton()
    if hasattr(SessionCostTracker, "reset_instance"):
        SessionCostTracker.reset_instance()
    if hasattr(BudgetEnforcer, "reset_instance"):
        BudgetEnforcer.reset_instance()

    # Reset FLUME VAE singleton to prevent state pollution across tests
    import cohezion.api as api_module
    if hasattr(api_module, '_vae_trainer'):
        api_module._vae_trainer = None

    # Reset RL policy singleton as well
    if hasattr(api_module, '_rl_policy'):
        api_module._rl_policy = None

    # Clear ALL logger handlers to prevent test pollution
    # Clear root logger
    logging.getLogger().handlers.clear()
    # Clear all named loggers
    for name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True  # Reset propagation

    yield

    # Reset after test
    reset_gate()  # Reset OllamaGate singleton
    reset_pool_manager()  # Reset ModelPoolManager singleton
    ExecutorFactory.reset_singleton()
    if hasattr(BatchableExecutor, "reset_singleton"):
        BatchableExecutor.reset_singleton()
    if hasattr(CostAwareRouter, "reset_singleton"):
        CostAwareRouter.reset_singleton()
    if hasattr(SessionCostTracker, "reset_instance"):
        SessionCostTracker.reset_instance()
    if hasattr(BudgetEnforcer, "reset_instance"):
        BudgetEnforcer.reset_instance()

    # Reset FLUME VAE singleton after test
    if hasattr(api_module, '_vae_trainer'):
        api_module._vae_trainer = None

    # Reset RL policy singleton after test
    if hasattr(api_module, '_rl_policy'):
        api_module._rl_policy = None

    # Clear ALL logger handlers after test too
    logging.getLogger().handlers.clear()
    for name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
