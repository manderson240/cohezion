"""Shared test fixtures for the Cohezion test suite."""

from __future__ import annotations

import asyncio
import logging
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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()
    else:
        yield


def _reset_all_singletons() -> None:
    """Reset critical singletons to prevent state pollution between tests."""
    import cohezion.api as api_module
    import cohezion.core.persistence.surreal_client as surreal_module
    from cohezion.compound.batch_executor import BatchableExecutor
    from cohezion.compound.executor import ExecutorFactory
    from cohezion.concurrency.ollama_gate import reset_gate
    from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer
    from cohezion.cost_optimization.cost_tracker import SessionCostTracker
    from cohezion.swarm.cost_aware_router import CostAwareRouter
    from cohezion.swarm.model_pool_manager import reset_pool_manager

    reset_gate()
    reset_pool_manager()
    ExecutorFactory.reset_singleton()
    if hasattr(BatchableExecutor, "reset_singleton"):
        BatchableExecutor.reset_singleton()
    if hasattr(CostAwareRouter, "reset_singleton"):
        CostAwareRouter.reset_singleton()
    if hasattr(SessionCostTracker, "reset_instance"):
        SessionCostTracker.reset_instance()
    if hasattr(BudgetEnforcer, "reset_instance"):
        BudgetEnforcer.reset_instance()

    if (
        hasattr(surreal_module, "_SHARED_STORE")
        and surreal_module._SHARED_STORE is not None
    ):
        if hasattr(surreal_module._SHARED_STORE, "_data"):
            surreal_module._SHARED_STORE._data.clear()
    surreal_module._SHARED_STORE = None

    if hasattr(api_module, "_vae_trainer"):
        api_module._vae_trainer = None

    if hasattr(api_module, "_rl_policy"):
        api_module._rl_policy = None

    logging.getLogger().handlers.clear()
    for name in list(logging.Logger.manager.loggerDict.keys()):
        lgr = logging.getLogger(name)
        lgr.handlers.clear()
        lgr.propagate = True


@pytest.fixture(autouse=True)
def reset_singletons():
    """Auto-reset critical singletons before and after each test."""
    _reset_all_singletons()
    yield
    _reset_all_singletons()
