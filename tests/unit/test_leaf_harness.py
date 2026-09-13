"""Unit tests for LeafHarness and LearnabilityCurriculumEngine (FrogNano architecture)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cohezion.agi.learnability_curriculum import (
    FrontierStatus,
    LearnabilityCurriculumEngine,
)
from cohezion.reliability.leaf_harness import (
    LeafHarness,
    LeafToolCall,
)


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "src").mkdir()
        (p / "src" / "example.py").write_text("def add(a, b):\n    return a + b\n")
        yield p


def test_leaf_harness_read_tool(temp_workspace):
    harness = LeafHarness(workspace_dir=temp_workspace)
    res = harness.execute_tool(
        LeafToolCall("read", {"path": "src/example.py", "start_line": 1, "end_line": 2})
    )
    assert res.success is True
    assert "def add(a, b):" in res.output


def test_leaf_harness_write_tool(temp_workspace):
    harness = LeafHarness(workspace_dir=temp_workspace)
    res = harness.execute_tool(
        LeafToolCall("write", {"path": "src/new_file.py", "content": "print('hello')"})
    )
    assert res.success is True
    assert (temp_workspace / "src" / "new_file.py").read_text() == "print('hello')"


def test_leaf_harness_edit_tool(temp_workspace):
    harness = LeafHarness(workspace_dir=temp_workspace)
    res = harness.execute_tool(
        LeafToolCall(
            "edit",
            {
                "path": "src/example.py",
                "target": "return a + b",
                "replacement": "return (a + b) * 2",
            },
        )
    )
    assert res.success is True
    assert "(a + b) * 2" in (temp_workspace / "src" / "example.py").read_text()


def test_leaf_harness_glob_tool(temp_workspace):
    harness = LeafHarness(workspace_dir=temp_workspace)
    res = harness.execute_tool(LeafToolCall("glob", {"pattern": "*.py", "directory": "src"}))
    assert res.success is True
    assert "src/example.py" in res.output


def test_leaf_harness_bash_tool_and_safety(temp_workspace):
    harness = LeafHarness(workspace_dir=temp_workspace)
    res = harness.execute_tool(LeafToolCall("bash", {"command": "echo 'Testing Leaf bash'"}))
    assert res.success is True
    assert "Testing Leaf bash" in res.output

    # Test safety filter
    res_unsafe = harness.execute_tool(LeafToolCall("bash", {"command": "rm -rf /"}))
    assert res_unsafe.success is False
    assert "safety policy" in res_unsafe.output


def test_leaf_harness_log_length_penalty(temp_workspace):
    harness = LeafHarness(workspace_dir=temp_workspace, token_penalty_weight=0.05)
    p0 = harness.compute_log_length_penalty(0)
    assert p0 == 0.0

    p100 = harness.compute_log_length_penalty(100)
    p1000 = harness.compute_log_length_penalty(1000)
    assert p100 > 0.0
    assert p1000 > p100


def test_learnability_curriculum_classification():
    engine = LearnabilityCurriculumEngine()
    # 0 attempts -> candidate frontier
    assert engine.classify_frontier_status(0, 0) == FrontierStatus.LEARNABILITY_FRONTIER

    # 10 attempts, 0 successes -> rate = 0.0 -> TOO_HARD
    assert engine.classify_frontier_status(10, 0) == FrontierStatus.TOO_HARD

    # 10 attempts, 10 successes -> rate = 1.0 -> TOO_EASY
    assert engine.classify_frontier_status(10, 10) == FrontierStatus.TOO_EASY

    # 10 attempts, 3 successes -> rate = 0.3 -> LEARNABILITY_FRONTIER
    assert engine.classify_frontier_status(10, 3) == FrontierStatus.LEARNABILITY_FRONTIER


@patch("urllib.request.urlopen")
def test_learnability_curriculum_registration(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'[{"result": [{"id": "synthetic_task:task_001"}]}]'
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    engine = LearnabilityCurriculumEngine()
    task = engine.register_synthetic_task(
        task_id="001",
        title="Fix port check error handling",
        target_module="cohezion/network.py",
        prompt="Write a socket checker",
        test_code="assert True",
        associated_neurons=["neuron:network_ports"],
    )
    assert task.task_id == "001"
    assert task.status == FrontierStatus.LEARNABILITY_FRONTIER
    assert mock_urlopen.called
