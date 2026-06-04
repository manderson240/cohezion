"""Unit and integration tests for UnifiedAgent with GAIA, Autocontext, AutoHarness, and Meta-Harness."""

import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.agent.unified_harness import UnifiedAgent


@pytest.fixture
def mock_executor():
    """Mock LLMExecutor."""
    executor = MagicMock()
    executor.execute_task = AsyncMock()
    return executor


@pytest.fixture
def temp_workdir(tmp_path):
    """Temporary working directory."""
    dir_path = tmp_path / "workdir"
    dir_path.mkdir()
    yield dir_path
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.mark.asyncio
async def test_unified_agent_basic_flow(mock_executor, temp_workdir):
    """Test that UnifiedAgent executes a task step-by-step and completes."""
    agent = UnifiedAgent(
        executor=mock_executor,
        use_gaia=False,
        use_autocontext=False,
        use_autoharness=False,
        use_metaharness=False,
    )

    # Mock planning next action to first run bash, then complete
    mock_executor.execute_task.side_effect = [
        MagicMock(output='{"tool": "bash", "args": {"command": "echo hello"}}'),
        MagicMock(output='{"complete": true, "result": {"status": "success"}}'),
    ]

    env = {"workdir": str(temp_workdir)}
    trace = await agent.run_task(task="Say hello and finish", env=env)

    assert trace.completed is True
    assert trace.final_state["status"] == "success"
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].tool_name == "bash"
    assert trace.tool_calls[0].arguments["command"] == "echo hello"


@pytest.mark.asyncio
async def test_unified_agent_gaia_integration(temp_workdir):
    """Test integration of GAIA SDK model routing."""
    mock_orch = AsyncMock()
    mock_orch.run.return_value = MagicMock(text='{"complete": true, "result": {"gaia": "success"}}')

    with patch("cohezion.agent.unified_harness.amd_optimized_hierarchy", return_value=mock_orch):
        agent = UnifiedAgent(
            use_gaia=True,
            use_autocontext=False,
            use_autoharness=False,
            use_metaharness=False,
        )

        assert agent.use_gaia is True
        assert agent.gaia_orchestrator == mock_orch

        env = {"workdir": str(temp_workdir)}
        trace = await agent.run_task(task="Run with GAIA", env=env)

        assert trace.completed is True
        assert trace.final_state["gaia"] == "success"
        mock_orch.run.assert_called_once()


@pytest.mark.asyncio
async def test_unified_agent_autocontext_compaction(mock_executor, temp_workdir):
    """Test Autocontext triggers log compaction on high context pressure."""
    agent = UnifiedAgent(
        executor=mock_executor,
        use_gaia=False,
        use_autocontext=True,
        use_autoharness=False,
        use_metaharness=False,
    )

    # Mock autocontext monitor warning
    mock_monitor = MagicMock(return_value={"pct": 0.85, "warn": True, "critical": False})

    # Mock executor output for planning and context compaction
    mock_executor.execute_task.side_effect = [
        MagicMock(output="This is compressed context summary"),  # Compaction call
        MagicMock(output='{"complete": true, "result": {"status": "done"}}'),  # Plan action call
    ]

    with patch("cohezion.agent.unified_harness.autocontext_monitor", mock_monitor):
        # Seed tool calls in trace to trigger history formatting
        env = {"workdir": str(temp_workdir)}
        trace = await agent.run_task(task="Run with compaction", env=env)

        assert trace.completed is True
        assert "Compressed Previous Steps" in trace.compressed_history
        assert "This is compressed context summary" in trace.compressed_history


@pytest.mark.asyncio
async def test_unified_agent_autoharness_validation(mock_executor, temp_workdir):
    """Test AutoHarness validation intercepts unsafe python actions."""
    agent = UnifiedAgent(
        executor=mock_executor,
        use_gaia=False,
        use_autocontext=False,
        use_autoharness=True,
        use_metaharness=False,
    )

    # 1. Synthesize a python verifier code block that checks if the action contains unsafe string
    verifier_code = """
def verify_action(state, action):
    if "import os" in action or "unsafe" in action:
        return False
    return True
"""
    mock_synthesizer = MagicMock()
    mock_synthesizer.synthesize_verifier = AsyncMock(return_value=verifier_code)

    # Mock planning next action to execute a python script containing "unsafe_function()"
    mock_executor.execute_task.side_effect = [
        MagicMock(output='{"tool": "python", "args": {"code": "unsafe_function()"}}'),
        MagicMock(output='{"complete": true, "result": {"status": "done"}}'),
    ]

    with patch(
        "cohezion.agent.unified_harness.AutoHarnessSynthesizer", return_value=mock_synthesizer
    ):
        env = {"workdir": str(temp_workdir)}
        trace = await agent.run_task(task="Run python verification", env=env)

        # The first tool call should be intercepted and rejected, not run,
        # then the loop continues to step 2 which completes.
        assert trace.completed is True
        assert len(trace.tool_calls) == 0  # Tool call rejected, never executed
        assert any("harness_rejection" in step for step in trace.steps)


@pytest.mark.asyncio
async def test_unified_agent_metaharness_trace_logging(mock_executor, temp_workdir):
    """Test Meta-Harness traces are written to the filesystem."""
    agent = UnifiedAgent(
        executor=mock_executor,
        use_gaia=False,
        use_autocontext=False,
        use_autoharness=False,
        use_metaharness=True,
    )

    mock_executor.execute_task.side_effect = [
        MagicMock(output='{"tool": "bash", "args": {"command": "echo test"}}'),
        MagicMock(output='{"complete": true, "result": {"status": "done"}}'),
    ]

    env = {"workdir": str(temp_workdir)}

    # Path patch to ensure files write under temporary path instead of real repo root if needed
    trace = await agent.run_task(task="Run Meta-Harness trace check", env=env)

    assert trace.completed is True

    # Check that execution_traces folder was created
    trace_dir = Path("execution_traces") / trace.task_id
    try:
        assert trace_dir.exists()

        # Verify JSON, metrics and output trace files exist
        json_files = list(trace_dir.glob("*.json"))
        metrics_files = list(trace_dir.glob("*.metrics"))
        output_files = list(trace_dir.glob("*.output"))

        assert len(json_files) == 1
        assert len(metrics_files) == 1
        assert len(output_files) == 1

        # Verify content of JSON trace
        trace_content = json.loads(json_files[0].read_text())
        assert trace_content["step"] == 0
        assert trace_content["action"]["tool"] == "bash"

    finally:
        # Cleanup trace folder
        shutil.rmtree(Path("execution_traces"), ignore_errors=True)
