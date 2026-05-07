"""Tests for the Agentic Task Environment."""

import json

import pytest

from cohezion.universe.agentic_env import (
    AgenticEnvironment,
    EnvObservation,
    SuccessCriterion,
    SuccessCriterionType,
    TaskScenario,
    ToolCall,
    ToolRegistry,
    ToolResult,
    ToolSpec,
    TrajectoryRecorder,
    build_coding_scenarios,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_scenario():
    return TaskScenario(
        scenario_id="test_001",
        name="Simple File Task",
        instructions="Create a file called 'output.txt' with the text 'hello world'.",
        initial_files={"input.txt": "some input data"},
        success_criteria=[
            SuccessCriterion(SuccessCriterionType.FILE_EXISTS, "output.txt"),
            SuccessCriterion(SuccessCriterionType.FILE_CONTAINS, "output.txt:hello world"),
        ],
        max_steps=10,
    )


@pytest.fixture
def env(simple_scenario):
    return AgenticEnvironment(simple_scenario)


# ---------------------------------------------------------------------------
# ToolRegistry tests
# ---------------------------------------------------------------------------


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = ToolSpec(
            name="test_tool",
            description="A test tool",
            parameters={"x": {"type": "string"}},
            handler=lambda args, state: f"got {args.get('x')}",
        )
        registry.register(tool)
        assert registry.get_tool("test_tool") is not None
        assert registry.get_tool("nonexistent") is None

    def test_available_tools(self):
        registry = ToolRegistry()
        tool = ToolSpec("t1", "desc", {}, lambda a, s: "ok")
        registry.register(tool)
        schemas = registry.available_tools
        assert len(schemas) == 1
        assert schemas[0]["name"] == "t1"

    def test_execute_success(self):
        registry = ToolRegistry()
        registry.register(ToolSpec("echo", "echo", {"msg": {}}, lambda a, s: a["msg"]))
        call = ToolCall(tool_name="echo", arguments={"msg": "hi"})
        response = registry.execute(call, {})
        assert response.result == ToolResult.SUCCESS
        assert response.output == "hi"

    def test_execute_unknown_tool(self):
        registry = ToolRegistry()
        call = ToolCall(tool_name="missing", arguments={})
        response = registry.execute(call, {})
        assert response.result == ToolResult.ERROR
        assert "Unknown tool" in response.output

    def test_execute_handler_error(self):
        registry = ToolRegistry()

        def bad_handler(a, s):
            raise ValueError("broken")

        registry.register(ToolSpec("bad", "bad", {}, bad_handler))
        call = ToolCall(tool_name="bad", arguments={})
        response = registry.execute(call, {})
        assert response.result == ToolResult.ERROR
        assert "broken" in response.output

    def test_call_count(self):
        registry = ToolRegistry()
        registry.register(ToolSpec("t", "t", {}, lambda a, s: "ok"))
        assert registry.call_count == 0
        registry.execute(ToolCall(tool_name="t", arguments={}), {})
        assert registry.call_count == 1
        registry.execute(ToolCall(tool_name="t", arguments={}), {})
        assert registry.call_count == 2


# ---------------------------------------------------------------------------
# AgenticEnvironment tests
# ---------------------------------------------------------------------------


class TestAgenticEnvironment:
    def test_reset(self, env):
        obs = env.reset()
        assert isinstance(obs, EnvObservation)
        assert obs.step_number == 0
        assert obs.remaining_steps == 10
        assert obs.coherence == 0.5
        assert "output.txt" not in obs.files_changed  # Only initial files
        assert "input.txt" in obs.files_changed

    def test_step_with_tool_call(self, env):
        env.reset()
        call = ToolCall(
            tool_name="file_write",
            arguments={"path": "output.txt", "content": "hello world"},
        )
        obs, reward, _done, _info = env.step(call)

        assert obs.step_number == 1
        assert obs.tool_response is not None
        assert obs.tool_response.result == ToolResult.SUCCESS
        assert isinstance(reward, float)

    def test_step_with_text_action(self, env):
        env.reset()
        obs, _reward, _done, _info = env.step("I want to read the input file")
        assert obs.step_number == 1
        assert obs.tool_response is None

    def test_file_read_tool(self, env):
        env.reset()
        call = ToolCall(tool_name="file_read", arguments={"path": "input.txt"})
        obs, _reward, _done, _info = env.step(call)
        assert obs.tool_response.output == "some input data"

    def test_file_list_tool(self, env):
        env.reset()
        call = ToolCall(tool_name="file_list", arguments={})
        obs, _reward, _done, _info = env.step(call)
        assert "input.txt" in obs.tool_response.output

    def test_bash_echo_tool(self, env):
        env.reset()
        call = ToolCall(tool_name="bash", arguments={"command": "echo hello"})
        obs, _reward, _done, _info = env.step(call)
        assert obs.tool_response.result == ToolResult.SUCCESS
        assert "hello" in obs.tool_response.output

    def test_success_detection(self, env):
        env.reset()
        # Write the correct file
        call = ToolCall(
            tool_name="file_write",
            arguments={"path": "output.txt", "content": "hello world"},
        )
        _obs, reward, done, info = env.step(call)

        assert done  # Task should be complete
        assert info.get("terminal_reason") == "success"
        assert reward > 0  # Success bonus

    def test_max_steps_termination(self, simple_scenario):
        simple_scenario.max_steps = 3
        env = AgenticEnvironment(simple_scenario)
        env.reset()

        for _i in range(3):
            _obs, _reward, done, info = env.step("noop action")

        assert done
        assert info.get("terminal_reason") == "max_steps"

    def test_coherence_tracking(self, env):
        env.reset()

        # Successful tool calls should maintain/improve coherence
        call = ToolCall(tool_name="file_list", arguments={})
        obs, _, _, _ = env.step(call)
        coherence_after_success = obs.coherence

        assert 0.0 <= coherence_after_success <= 1.0

    def test_error_penalty(self, env):
        env.reset()
        # Try to read a nonexistent file
        call = ToolCall(tool_name="file_read", arguments={"path": "nonexistent.txt"})
        obs, reward, _done, _info = env.step(call)

        assert obs.tool_response.result == ToolResult.ERROR
        # Error should penalize reward
        assert reward < 0.5

    def test_trajectory_recording(self, env):
        env.reset()
        call = ToolCall(tool_name="file_list", arguments={})
        env.step(call)
        env.step("text action")

        trajectory = env.trajectory
        assert len(trajectory) == 2
        assert trajectory[0].step_number == 1
        assert trajectory[1].step_number == 2

    def test_export_trajectory(self, env):
        env.reset()
        call = ToolCall(
            tool_name="file_write",
            arguments={"path": "output.txt", "content": "hello world"},
        )
        env.step(call)

        exported = env.export_trajectory()
        assert exported["scenario_id"] == "test_001"
        assert exported["total_steps"] == 1
        assert len(exported["steps"]) == 1
        assert "tool" in exported["steps"][0]["action"]


# ---------------------------------------------------------------------------
# TaskScenario tests
# ---------------------------------------------------------------------------


class TestTaskScenario:
    def test_creation(self):
        scenario = TaskScenario(
            scenario_id="s1",
            name="Test",
            instructions="Do something",
            initial_files={"a.py": "print('hello')"},
            max_steps=20,
        )
        assert scenario.scenario_id == "s1"
        assert len(scenario.initial_files) == 1

    def test_build_coding_scenarios(self):
        scenarios = build_coding_scenarios()
        assert len(scenarios) >= 3
        for s in scenarios:
            assert s.scenario_id
            assert s.instructions
            assert s.max_steps > 0


# ---------------------------------------------------------------------------
# TrajectoryRecorder tests
# ---------------------------------------------------------------------------


class TestTrajectoryRecorder:
    def test_record_and_export(self, simple_scenario, tmp_path):
        recorder = TrajectoryRecorder(output_dir=str(tmp_path / "traj"))

        env = AgenticEnvironment(simple_scenario)
        env.reset()
        env.step(
            ToolCall(
                tool_name="file_write",
                arguments={"path": "output.txt", "content": "hello world"},
            )
        )
        recorder.record(env)

        assert recorder.trajectory_count == 1

        path = recorder.export_jsonl()
        assert path.exists()
        with open(path) as f:
            data = json.loads(f.readline())
        assert data["scenario_id"] == "test_001"

    def test_stats(self, simple_scenario, tmp_path):
        recorder = TrajectoryRecorder(output_dir=str(tmp_path / "traj"))

        # Record successful run
        env = AgenticEnvironment(simple_scenario)
        env.reset()
        env.step(
            ToolCall(
                tool_name="file_write",
                arguments={"path": "output.txt", "content": "hello world"},
            )
        )
        recorder.record(env)

        stats = recorder.get_stats()
        assert stats["count"] == 1
        assert 0.0 <= stats["success_rate"] <= 1.0

    def test_empty_stats(self, tmp_path):
        recorder = TrajectoryRecorder(output_dir=str(tmp_path / "traj"))
        stats = recorder.get_stats()
        assert stats["count"] == 0

    def test_preference_pairs(self, simple_scenario, tmp_path):
        recorder = TrajectoryRecorder(output_dir=str(tmp_path / "traj"))

        # Record successful run
        env1 = AgenticEnvironment(simple_scenario)
        env1.reset()
        env1.step(
            ToolCall(
                tool_name="file_write",
                arguments={"path": "output.txt", "content": "hello world"},
            )
        )
        recorder.record(env1)

        # Record failed run (doesn't write the correct file)
        env2 = AgenticEnvironment(simple_scenario)
        env2.reset()
        env2.step("I don't know what to do")
        env2.step("still confused")
        recorder.record(env2)

        path = recorder.export_preference_pairs()
        assert path.exists()

        with open(path) as f:
            lines = f.readlines()
        # Should have at least one pair (1 success × 1 failure)
        assert len(lines) >= 1
