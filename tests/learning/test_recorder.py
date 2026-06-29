"""Tests for cohezion.learning.recorder.

All external I/O (PrecipitationBus, MyceliumRegistry, OuroborosEngine) is
mocked or stubbed. We verify that success and failure paths emit the expected
learning artifacts.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.learning.recorder import (
    LearningRecorder,
    get_learning_recorder,
    reset_learning_recorder,
)


@pytest.fixture
def recorder():
    """Fresh recorder with mocked engine/registry."""
    engine = MagicMock()
    engine.consume_exhaust = MagicMock(return_value=False)
    registry = MagicMock()
    registry.ingest_entry = MagicMock()
    yield LearningRecorder(ouroboros_engine=engine, mycelium_registry=registry)
    reset_learning_recorder()


@patch("cohezion.learning.recorder.emit")
def test_record_agent_turn_emits_witness_mark(mock_emit, recorder):
    recorder.record_agent_turn(
        agent_name="TestAgent",
        prompt="hello",
        response="hi",
        model="gemma-4-e2b-it-gguf",
        lane="npu",
        phi_score=0.8,
        confidence=0.9,
        latency_ms=10.0,
        escalated_to_cloud=False,
    )
    assert mock_emit.called
    event = mock_emit.call_args[0][0]
    assert event.kind.value == "witness_mark"
    assert event.agent_id == "TestAgent"
    assert event.payload["lane"] == "npu"
    assert event.payload["escalated_to_cloud"] is False
    assert recorder._mycelium.ingest_entry.called


@patch("cohezion.learning.recorder.emit")
def test_record_executor_outcome_success_path(mock_emit, recorder):
    recorder.record_executor_outcome(
        task_description="do a thing",
        skill_name="test_skill",
        success=True,
        output="done",
        metrics={"coherence": 0.75, "tokens_used": 42},
        duration_seconds=1.2,
        project="test",
    )
    assert mock_emit.called
    event = mock_emit.call_args[0][0]
    assert event.kind.value == "witness_mark"
    assert event.payload["success"] is True
    assert recorder._mycelium.ingest_entry.called
    recorder._ouroboros.consume_exhaust.assert_not_called()


@patch("cohezion.learning.recorder.emit")
def test_record_executor_outcome_failure_triggers_ouroboros(mock_emit, recorder):
    recorder.record_executor_outcome(
        task_description="do a thing",
        skill_name="test_skill",
        success=False,
        output="Error: something failed",
        metrics={"coherence": 0.2, "tokens_used": 10},
        duration_seconds=0.5,
        project="test",
    )
    assert mock_emit.called
    event = mock_emit.call_args[0][0]
    assert event.payload["success"] is False
    assert recorder._mycelium.ingest_entry.called
    recorder._ouroboros.consume_exhaust.assert_called_once()


def test_get_learning_recorder_singleton():
    a = get_learning_recorder()
    b = get_learning_recorder()
    assert a is b
    reset_learning_recorder()
    c = get_learning_recorder()
    assert c is not a
