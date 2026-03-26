"""Tests for CohezionWorkflow."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cohezion.agentjet.workflow import CohezionWorkflow


def _make_mock_result(
    output: str = "test output",
    success: bool = True,
    coherence: float = 0.8,
    skill_name: str = "research",
    phi_score: float = 0.85,
    duration_seconds: float = 1.2,
):
    result = MagicMock()
    result.output = output
    result.success = success
    result.metrics = {"coherence": coherence}
    result.skill_name = skill_name
    result.duration_seconds = duration_seconds
    return result


@pytest.fixture
def mock_executor():
    executor = MagicMock()
    executor.execute_task = MagicMock(return_value=_make_mock_result())
    return executor


@pytest.fixture
def mock_tracker():
    tracker = MagicMock()
    point = MagicMock()
    point.metadata = {"phi_score": 0.85}
    point.coherence = 0.8
    tracker.track_execution = MagicMock(return_value=point)
    return tracker


@pytest.fixture
def workflow(mock_executor, mock_tracker) -> CohezionWorkflow:
    return CohezionWorkflow(executor=mock_executor, tracker=mock_tracker)


@pytest.mark.asyncio
async def test_run_returns_tuple_of_output_and_metadata(workflow: CohezionWorkflow) -> None:
    task = {"description": "Write a test", "skill_name": "coding"}
    result = await workflow.run(task)
    assert isinstance(result, tuple)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_run_metadata_has_phi_score(workflow: CohezionWorkflow) -> None:
    task = {"description": "Analyze data", "skill_name": "analysis"}
    _, metadata = await workflow.run(task)
    assert "phi_score" in metadata
    assert isinstance(metadata["phi_score"], float)


@pytest.mark.asyncio
async def test_run_metadata_has_skill_name(workflow: CohezionWorkflow) -> None:
    task = {"description": "Generate code", "skill_name": "coding"}
    _, metadata = await workflow.run(task)
    assert "skill_name" in metadata
    assert isinstance(metadata["skill_name"], str)
    assert metadata["skill_name"] == "coding"


@pytest.mark.asyncio
async def test_run_metadata_has_required_keys(workflow: CohezionWorkflow) -> None:
    task = {"description": "Test task"}
    _, metadata = await workflow.run(task)
    for key in ("phi_score", "skill_name", "coherence", "success", "duration_seconds"):
        assert key in metadata, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_run_executor_failure_returns_phi_zero(mock_tracker: MagicMock) -> None:
    failing_executor = MagicMock()
    failing_executor.execute_task = MagicMock(side_effect=RuntimeError("executor blew up"))
    workflow = CohezionWorkflow(executor=failing_executor, tracker=mock_tracker)

    task = {"description": "Failing task"}
    output, metadata = await workflow.run(task)

    assert metadata["phi_score"] == 0.0
    assert metadata["success"] is False
    assert "[error]" in output


@pytest.mark.asyncio
async def test_run_uses_default_skill_name_when_missing(workflow: CohezionWorkflow) -> None:
    task = {"description": "Some task"}
    _, metadata = await workflow.run(task)
    assert metadata["skill_name"] == "general"


@pytest.mark.asyncio
async def test_run_output_is_string(workflow: CohezionWorkflow) -> None:
    task = {"description": "Return something", "skill_name": "coding"}
    output, _ = await workflow.run(task)
    assert isinstance(output, str)


@pytest.mark.asyncio
async def test_run_empty_description_does_not_raise(workflow: CohezionWorkflow) -> None:
    task = {"description": ""}
    # Should not raise, just warn
    output, metadata = await workflow.run(task)
    assert isinstance(output, str)


@pytest.mark.asyncio
async def test_run_tracker_failure_falls_back_gracefully(mock_executor: MagicMock) -> None:
    broken_tracker = MagicMock()
    broken_tracker.track_execution = MagicMock(side_effect=Exception("tracker down"))
    workflow = CohezionWorkflow(executor=mock_executor, tracker=broken_tracker)

    task = {"description": "Track this", "skill_name": "research"}
    output, metadata = await workflow.run(task)

    # Falls back to coherence from result metrics
    assert "phi_score" in metadata
    assert isinstance(metadata["phi_score"], float)
