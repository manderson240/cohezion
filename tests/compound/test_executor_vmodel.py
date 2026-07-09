"""V-model structural invariant tests for CompoundExecutor.execute_task.

Structural tests fire at harness start time — before behavioral tests.
They verify interface contracts (types, presence of fields) not behavior.
"""

import inspect
from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.executor import CompoundExecutor, ExecutionResult


@pytest.fixture
def executor():
    with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
        exc = CompoundExecutor(mcp_client=MagicMock())
    exc.logger = MagicMock()
    exc.logger.get_experience_guidance.return_value = {"relevant_context": [], "guidance": "stub"}
    exc.logger.log_execution_start.return_value = "exp/path/123"
    exc.logger.log_execution_result = MagicMock()
    exc._try_template_match = MagicMock(return_value=None)
    exc._context_loaded = True
    return exc


class TestExecutorVModelStructure:
    """V-model O1: execute_task structural signature invariants."""

    def test_execute_task_accepts_required_positional_args(self, executor):
        """O1a: execute_task accepts task_description, skill_name, operation_type, execute_fn."""
        sig = inspect.signature(executor.execute_task)
        params = list(sig.parameters.keys())
        for required in ["task_description", "skill_name", "operation_type", "execute_fn"]:
            assert required in params, f"execute_task missing required param: {required}"

    def test_execute_task_returns_execution_result(self, executor):
        """O1b: execute_task always returns ExecutionResult (not None, not dict)."""
        result = executor.execute_task(
            "Desc", "skill", "generate", lambda g: ("out", {"coherence": 0.8})
        )
        assert isinstance(result, ExecutionResult), (
            f"execute_task must return ExecutionResult, got {type(result)}"
        )

    def test_execution_result_has_required_fields(self, executor):
        """O1c: ExecutionResult must have success, output, metrics fields."""
        result = executor.execute_task(
            "Desc", "skill", "generate", lambda g: ("out", {"coherence": 0.8})
        )
        assert hasattr(result, "success"), "ExecutionResult missing .success"
        assert hasattr(result, "output"), "ExecutionResult missing .output"
        assert hasattr(result, "metrics"), "ExecutionResult missing .metrics"

    def test_success_field_is_bool(self, executor):
        """O1d: ExecutionResult.success must be bool."""
        result = executor.execute_task(
            "Desc", "skill", "generate", lambda g: ("out", {"coherence": 0.8})
        )
        assert isinstance(result.success, bool), (
            f"ExecutionResult.success must be bool, got {type(result.success)}"
        )

    def test_output_field_is_str(self, executor):
        """O1e: ExecutionResult.output must be str."""
        result = executor.execute_task(
            "Desc", "skill", "generate", lambda g: ("output text", {"coherence": 0.7})
        )
        assert isinstance(result.output, str), (
            f"ExecutionResult.output must be str, got {type(result.output)}"
        )

    def test_metrics_field_is_dict(self, executor):
        """O1f: ExecutionResult.metrics must be dict."""
        result = executor.execute_task(
            "Desc", "skill", "generate", lambda g: ("out", {"coherence": 0.8})
        )
        assert isinstance(result.metrics, dict), (
            f"ExecutionResult.metrics must be dict, got {type(result.metrics)}"
        )

    def test_drr_gate_is_advisory_not_blocking(self, executor):
        """O2: DRR gate failures must not prevent result.success=True.

        DRR (Design Review Report) was made advisory-only this session.
        A low-coherence output that triggers DRR failure should still return
        result.success=True if the execute_fn itself succeeded.
        """
        result = executor.execute_task(
            task_description="Low quality task",
            skill_name="test",
            operation_type="generate",
            execute_fn=lambda g: (
                "output",
                {"coherence": 0.05},
            ),  # Very low coherence → triggers DRR
        )
        # DRR may log warnings but must not set result.success = False
        assert result.success is True, (
            "DRR gate is blocking execution (result.success=False). DRR should be advisory-only."
        )

    def test_failed_execute_fn_sets_success_false(self, executor):
        """O3: If execute_fn raises, result.success must be False."""

        def failing_fn(guidance):
            raise ValueError("deliberate failure")

        result = executor.execute_task("Desc", "skill", "generate", failing_fn)
        assert result.success is False
        assert "deliberate failure" in result.output
