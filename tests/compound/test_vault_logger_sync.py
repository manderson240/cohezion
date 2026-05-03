"""Tests for VaultLogger sync MCP API usage (Task #16).

Ensures VaultLogger uses the sync variants (vault_write_sync, vault_read_sync,
vault_delete_sync) and does not produce unawaited-coroutine warnings.
"""

from __future__ import annotations

import warnings
from datetime import datetime
from unittest.mock import MagicMock

from cohezion.compound.exp_persistence.vault import ExecutionContext, VaultLogger


def _make_ctx(start: datetime | None = None) -> ExecutionContext:
    return ExecutionContext(
        project="cohezion",
        skill_name="test_skill",
        task_description="unit test task",
        operation_type="analyze",
        start_time=start or datetime.now(),
        mcp_client=None,
    )


def test_log_execution_start_uses_vault_write_sync():
    """log_execution_start must call mcp.vault_write_sync, not mcp.vault_write."""
    mcp = MagicMock()
    mcp.vault_write_sync = MagicMock(return_value=None)
    mcp.vault_write = MagicMock()  # would raise if called as coroutine

    vl = VaultLogger(mcp_client=mcp)
    ctx = _make_ctx()

    path = vl.log_execution_start(ctx)

    assert path != "", "expected a non-empty experiment path"
    assert mcp.vault_write_sync.called, "vault_write_sync should be invoked"
    assert not mcp.vault_write.called, "vault_write (async variant) must not be invoked"


def test_vault_write_sync_no_unawaited_warning():
    """Even when vault_write_sync raises, no RuntimeWarning about unawaited coroutines."""
    mcp = MagicMock()
    mcp.vault_write_sync = MagicMock(side_effect=RuntimeError("vault write failed"))

    vl = VaultLogger(mcp_client=mcp)
    ctx = _make_ctx()

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        path = vl.log_execution_start(ctx)

    # Failure path returns "" rather than raising
    assert path == ""
    coro_warnings = [
        w for w in captured if "coroutine" in str(w.message).lower() and "await" in str(w.message).lower()
    ]
    assert not coro_warnings, f"unexpected coroutine warnings: {coro_warnings}"


def test_vault_read_sync_returns_empty_on_failure():
    """A read failure during log_execution_result must not raise."""
    mcp = MagicMock()
    mcp.vault_read_sync = MagicMock(side_effect=RuntimeError("read failed"))
    mcp.vault_write_sync = MagicMock(return_value=None)

    vl = VaultLogger(mcp_client=mcp)

    # Should swallow the error (returns None implicitly)
    result = vl.log_execution_result(
        experiment_path="experiments/cohezion/test/123.json",
        success=True,
        output="ok",
        metrics={"coherence": 0.5},
    )
    assert result is None


def test_vault_logger_full_cycle_no_exceptions():
    """Full lifecycle (start → result → extract pattern) must not raise."""
    mcp = MagicMock()
    mcp.vault_write_sync = MagicMock(return_value=None)
    # vault_read_sync needs to return JSON-parseable content for log_execution_result
    mcp.vault_read_sync = MagicMock(return_value='{"status": "started"}')

    vl = VaultLogger(mcp_client=mcp)
    ctx = _make_ctx()

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        path = vl.log_execution_start(ctx)
        vl.log_execution_result(
            experiment_path=path,
            success=True,
            output="completed cleanly",
            metrics={"coherence": 0.7, "anomaly_score": 0.1},
        )
        extracted = vl.extract_execution_pattern(
            source_path=path,
            pattern_name="sync_pattern",
            description="Sync vault API usage",
            code_example="vl.log_execution_start(ctx)",
            domain="compound",
        )

    assert extracted != ""
    # No coroutine warnings throughout the full cycle
    coro_warnings = [w for w in captured if "coroutine" in str(w.message).lower()]
    assert not coro_warnings, f"unexpected coroutine warnings: {coro_warnings}"


def test_delete_operation_uses_vault_delete_sync():
    """_prune_traces (when triggered) must call vault_delete_sync, not vault_delete."""
    mcp = MagicMock()
    mcp.vault_write_sync = MagicMock(return_value=None)
    # Return more than max_traces=100 so pruning fires
    fake_traces = [f"execution_traces/test_skill/{i:010d}_analyze.json" for i in range(150)]
    mcp.vault_search = MagicMock(return_value=fake_traces)
    mcp.vault_delete_sync = MagicMock(return_value=None)
    mcp.vault_delete = MagicMock()  # async variant — must not be called

    vl = VaultLogger(mcp_client=mcp)
    ctx = _make_ctx()

    trace_path = vl.log_execution_trace(
        ctx=ctx,
        success=True,
        output="ok",
        metrics={"coherence": 0.6},
    )

    assert trace_path != ""
    assert mcp.vault_delete_sync.called, "vault_delete_sync must be invoked during pruning"
    assert not mcp.vault_delete.called, "vault_delete (async variant) must not be invoked"
    # Should have removed 150 - 100 = 50 oldest traces
    assert mcp.vault_delete_sync.call_count == 50
