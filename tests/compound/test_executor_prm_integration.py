"""Integration tests — ProcessRewardModel wired into CompoundExecutor.

Verifies the structural wiring from executor_factory.py → executor.py → PRM:
  1. ExecutorFactory.create() auto-creates a ProcessRewardModel
  2. begin_execution() is called once per execute_task() call
  3. record_step() is called for the 'execute_fn' step (step 3)
  4. finalize() is called and prm_* metrics appear in result
  5. PRM failure does NOT break execute_task()
  6. execute_task() works without a PRM (process_reward_model=None)
  7. Structural: CompoundExecutor.__init__ accepts process_reward_model param

All external I/O (MCP, vault, PRM HTTP) is mocked.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.executor_factory import ExecutorFactory
from cohezion.compound.process_reward_model import ProcessRewardModel, StepScoreRecord


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_executor(prm=None) -> CompoundExecutor:
    """Build a CompoundExecutor with vault stubbed out, optionally injecting a PRM."""
    with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
        exc = CompoundExecutor(mcp_client=MagicMock(), process_reward_model=prm)
    exc.logger = MagicMock()
    exc.logger.get_experience_guidance.return_value = {"relevant_context": [], "guidance": ""}
    exc.logger.log_execution_start.return_value = "exp/path/test"
    exc.logger.log_execution_result = MagicMock()
    exc._try_template_match = MagicMock(return_value=None)
    exc._context_loaded = True
    return exc


def _simple_execute_fn(_guidance):
    return "output text", {"custom_metric": 1}


def _mock_prm(record_id: str = "rid_test", dense_reward: float = 0.8) -> MagicMock:
    """Build a ProcessRewardModel mock with pre-configured return values."""
    mock = MagicMock(spec=ProcessRewardModel)
    mock.begin_execution.return_value = record_id
    mock.record_step.return_value = MagicMock()
    record = StepScoreRecord(record_id=record_id, task_description="task")
    mock.finalize.return_value = record
    mock.to_metrics_dict.return_value = {
        "prm_dense_reward": dense_reward,
        "prm_step_count": 2,
        "prm_pass_rate": 1.0,
        "prm_min_step_score": dense_reward - 0.1,
    }
    return mock


# ---------------------------------------------------------------------------
# 1. ExecutorFactory auto-creates PRM when none supplied
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_executor_factory_auto_creates_prm():
    """ExecutorFactory.create() without explicit PRM injects a ProcessRewardModel."""
    mcp = MagicMock()
    disabled_prm = ProcessRewardModel(enabled=False)
    with (
        patch("cohezion.compound.exp_persistence.vault.VaultLogger"),
        patch("cohezion.compound.maker_checker.build_maker_checker", return_value=None),
        patch(
            "cohezion.compound.process_reward_model.build_process_reward_model",
            return_value=disabled_prm,
        ) as mock_build,
    ):
        executor = ExecutorFactory.create(mcp)
    mock_build.assert_called_once()
    assert executor._process_reward_model is disabled_prm


@pytest.mark.unit
def test_executor_factory_honours_explicit_prm():
    """ExecutorFactory.create() passes through an explicit process_reward_model unchanged."""
    mcp = MagicMock()
    explicit_prm = ProcessRewardModel(enabled=False)
    with (
        patch("cohezion.compound.exp_persistence.vault.VaultLogger"),
        patch("cohezion.compound.maker_checker.build_maker_checker", return_value=None),
    ):
        executor = ExecutorFactory.create(mcp, process_reward_model=explicit_prm)
    assert executor._process_reward_model is explicit_prm


# ---------------------------------------------------------------------------
# 2. begin_execution called once per execute_task
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prm_begin_execution_called_once_per_run():
    """execute_task() calls prm.begin_execution exactly once per call."""
    mock = _mock_prm()
    executor = _make_executor(prm=mock)
    executor.execute_task("task desc", "skill", "generate", _simple_execute_fn)
    mock.begin_execution.assert_called_once_with("task desc")


# ---------------------------------------------------------------------------
# 3. record_step called for execute_fn step (step 3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prm_record_step_called_for_execute_fn():
    """execute_task() calls prm.record_step with step_id='3' for the execute_fn step."""
    mock = _mock_prm()
    executor = _make_executor(prm=mock)
    executor.execute_task("task desc", "skill", "generate", _simple_execute_fn)

    step_ids = [c.args[1] for c in mock.record_step.call_args_list]
    assert "3" in step_ids, f"Expected step_id '3' among {step_ids}"


# ---------------------------------------------------------------------------
# 4. finalize called and prm_* metrics appear in result
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prm_finalize_called_and_metrics_merged():
    """execute_task() calls prm.finalize() and merges prm_* keys into result.metrics."""
    mock = _mock_prm(record_id="rid_abc", dense_reward=0.75)
    executor = _make_executor(prm=mock)
    result = executor.execute_task("task desc", "skill", "generate", _simple_execute_fn)

    mock.finalize.assert_called_once_with("rid_abc")
    assert "prm_dense_reward" in result.metrics
    assert result.metrics["prm_dense_reward"] == 0.75
    assert "prm_step_count" in result.metrics
    assert "prm_pass_rate" in result.metrics
    assert "prm_min_step_score" in result.metrics


# ---------------------------------------------------------------------------
# 5. PRM failure does NOT break execute_task
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prm_begin_execution_error_does_not_break_executor():
    """If prm.begin_execution() raises, execute_task still returns success."""
    mock = MagicMock(spec=ProcessRewardModel)
    mock.begin_execution.side_effect = RuntimeError("PRM unavailable")
    executor = _make_executor(prm=mock)
    result = executor.execute_task("task desc", "skill", "generate", _simple_execute_fn)
    assert result.success is True
    assert result.output == "output text"


@pytest.mark.unit
def test_prm_finalize_error_does_not_break_executor():
    """If prm.finalize() raises, execute_task still returns success."""
    mock = MagicMock(spec=ProcessRewardModel)
    mock.begin_execution.return_value = "rid_fail"
    mock.record_step.return_value = MagicMock()
    mock.finalize.side_effect = RuntimeError("finalize explodes")
    executor = _make_executor(prm=mock)
    result = executor.execute_task("task desc", "skill", "generate", _simple_execute_fn)
    assert result.success is True


# ---------------------------------------------------------------------------
# 6. No PRM (process_reward_model=None) → execute_task still succeeds
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_execute_task_succeeds_without_prm():
    """execute_task() works correctly when process_reward_model is None."""
    executor = _make_executor(prm=None)
    result = executor.execute_task("task desc", "skill", "generate", _simple_execute_fn)
    assert result.success is True
    assert "prm_dense_reward" not in result.metrics


# ---------------------------------------------------------------------------
# 7. Structural: executor __init__ accepts process_reward_model kwarg
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_executor_init_accepts_process_reward_model_param():
    """CompoundExecutor.__init__ signature must include process_reward_model parameter.

    Structural guard (V-Model Learning 366): catches drift before behavioral tests reach
    the TypeError deep in the call stack.
    """
    sig = inspect.signature(CompoundExecutor.__init__)
    assert "process_reward_model" in sig.parameters, (
        "CompoundExecutor.__init__ missing process_reward_model parameter — "
        "ExecutorFactory.create() wiring would break silently"
    )
