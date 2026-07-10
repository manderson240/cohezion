"""Ring-4 wiring: execute_task persists real cycles via compound_persist (2026-07-10).

Invariant (harness-style): persist_cycle had ZERO callers after landing —
the compound graph never accumulated. These tests pin the wiring so a refactor
can't silently orphan it again.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

from cohezion.compound.executor import CompoundExecutor


def _executor(**kw):
    return CompoundExecutor(MagicMock(), enable_guardrails=False, **kw)


def _run(ex):
    return ex.execute_task(
        task_description="wiring test task",
        skill_name="wiring-test",
        operation_type="generate",
        execute_fn=lambda g: ("output", {"quality_score": 0.9, "tier_used": "npu"}),
    )


def test_structural_execute_task_references_persist_cycle():
    src = inspect.getsource(CompoundExecutor.execute_task)
    assert "persist_cycle" in src and "_enable_cycle_persistence" in src


def test_cycle_persisted_when_enabled():
    ex = _executor(enable_cycle_persistence=True)
    with patch("cohezion.compound.compound_persist.persist_cycle") as pc:
        result = _run(ex)
    assert result.success
    assert pc.call_count == 1
    point, temp_result = pc.call_args.args
    assert temp_result.success is True
    kwargs = pc.call_args.kwargs
    assert kwargs["skill_name"] == "wiring-test"
    assert kwargs["run_id"].startswith("cycle-")
    # learning is a factual metric summary, never fabricated narrative
    assert "quality=0.9" in kwargs["learning"] and "tier=npu" in kwargs["learning"]


def test_cycle_not_persisted_by_default():
    ex = _executor()  # direct construction = test isolation, stays off
    with patch("cohezion.compound.compound_persist.persist_cycle") as pc:
        result = _run(ex)
    assert result.success
    pc.assert_not_called()


def test_persistence_failure_is_non_blocking():
    ex = _executor(enable_cycle_persistence=True)
    with patch(
        "cohezion.compound.compound_persist.persist_cycle",
        side_effect=RuntimeError("surreal down"),
    ):
        result = _run(ex)
    assert result.success  # the task must not fail because the ledger write did


def test_make_executor_enables_cycle_persistence():
    src = inspect.getsource(
        __import__("cohezion.compound", fromlist=["make_executor"]).make_executor
    )
    assert 'setdefault("enable_cycle_persistence", True)' in src
