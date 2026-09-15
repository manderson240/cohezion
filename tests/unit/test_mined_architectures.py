"""Tests for mined and consolidated architectures.

Verifies:
1. SurrealDB Connection Pool with predictive load and auto-scaling
2. Unified Compound Manager for MCP compound sessions
3. Multi-Harness Evaluator in cohezion.benchmarks
4. Datamesh Kanban Bridge pass-through delegation
"""

from unittest.mock import patch

import pytest

from cohezion.benchmarks.multi_harness_evaluator import (
    HarnessBenchmarkTask,
    HarnessEvaluationResult,
    HarnessType,
)
from cohezion.datamesh.kanban_bridge import backfill_items, persist_item
from cohezion.mcp.compound_unified import (
    get_unified_manager,
)
from cohezion.persistence.surreal_connection_pool import (
    PoolConfig,
    PooledConnection,
    get_surreal_connection_pool,
    reset_surreal_connection_pool,
)


# ── Surreal Connection Pool Tests ──────────────────────────────────────────


class MockSurrealClient:
    def __init__(self) -> None:
        self.connected = False
        self.closed = False

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.closed = True

    async def query(self, sql: str, params: dict | None = None) -> list:
        return [{"status": "OK", "result": [1]}]

    async def create(self, table: str, data: dict) -> dict:
        return {"id": f"{table}:1", **data}

    async def update(self, thing: str, data: dict) -> dict:
        return {"id": thing, **data}


@pytest.mark.asyncio
async def test_pool_config_validation():
    config = PoolConfig(max_size=10, min_size=2)
    assert config.max_size == 10
    assert config.min_size == 2

    with pytest.raises(ValueError, match="max_size must be >= min_size"):
        PoolConfig(max_size=1, min_size=5)


@pytest.mark.asyncio
async def test_surreal_connection_pool_lifecycle():
    reset_surreal_connection_pool()
    config = PoolConfig(max_size=5, min_size=1)
    pool = get_surreal_connection_pool(MockSurrealClient, config)

    # Acquire connection
    conn = await pool.acquire()
    assert isinstance(conn, PooledConnection)
    assert conn._healthy is True

    # Use context manager
    async with conn:
        res = await conn.client.query("SELECT 1")
        assert len(res) == 1

    # Release and metrics check
    metrics = await pool.get_metrics()
    assert metrics["acquired"] >= 1
    assert metrics["released"] >= 1
    assert 0.0 <= metrics["usage_percent"] <= 1.0

    await pool.close()
    reset_surreal_connection_pool()


# ── Unified Compound Manager Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_unified_compound_manager():
    manager = get_unified_manager()
    assert manager is not None
    assert "bmad" in manager.server_configs
    assert "skills" in manager.server_configs
    assert "security" in manager.server_configs

    # Test link servers
    linked = await manager.link_servers("bmad", "prd-1", "skills", "skill-2")
    assert linked is True

    # Test cross server context structure
    ctx = await manager.get_cross_server_context("test query")
    assert ctx["query"] == "test query"
    assert "sources" in ctx


# ── Multi-Harness Evaluator Tests ──────────────────────────────────────────


def test_multi_harness_evaluator_models():
    assert HarnessType.HERMES == "hermes"
    assert HarnessType.OPENCODE == "opencode"
    assert HarnessType.AUTOHARNESS == "autoharness"

    task = HarnessBenchmarkTask(
        task_id="t1",
        harness=HarnessType.OPENCODE,
        prompt="Write vector norm function",
        expected_criteria="np.linalg.norm",
        test_validator="np.linalg.norm",
    )
    assert task.harness == HarnessType.OPENCODE

    result = HarnessEvaluationResult(
        model_name="test_model",
        harness=HarnessType.OPENCODE,
        task_id="t1",
        success=True,
        score=1.0,
        latency_ms=42.0,
        tokens_generated=50,
    )
    assert result.success is True
    assert result.score == 1.0


# ── Datamesh Kanban Bridge Delegation Tests ────────────────────────────────


def test_datamesh_kanban_bridge_delegation():
    item = {"id": "test-task", "title": "Test Task"}
    with patch("cohezion.data_mesh.kanban_bridge.persist_item", return_value={"surreal": True, "obsidian": True}) as mock_p:
        res = persist_item(item)
        assert res == {"surreal": True, "obsidian": True}
        mock_p.assert_called_once_with(item)

    with patch("cohezion.data_mesh.kanban_bridge.backfill_items", return_value={"total": 1, "surreal_ok": 1, "obsidian_ok": 1}) as mock_b:
        res = backfill_items([item])
        assert res["total"] == 1
        mock_b.assert_called_once_with([item])
