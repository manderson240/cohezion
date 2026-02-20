"""Tests for real embodied environments.

Validates that browser, shell, and API environments execute real actions
and produce verifiable outcomes.
"""

from __future__ import annotations

import pytest
import asyncio
import tempfile
from pathlib import Path

# Import real environment classes
from cohezion.real_envs.base import (
    RealAction,
    RealObservation,
    RealState,
    TrajectorySegment,
)
from cohezion.real_envs.shell_env import (
    ShellEnvironment,
    ShellAction,
    ShellObservation,
)
from cohezion.real_envs.evaluator import (
    RealEnvironmentEvaluator,
    EvaluatedTask,
    FileExistsCriterion,
    FileContentCriterion,
)
from cohezion.real_envs.tasks.scenarios import get_task, list_tasks
from cohezion.real_envs.journey_tracker import RealEnvironmentJourneyTracker
from cohezion.real_envs.metrics import RealEnvironmentMetricsCollector


@pytest.mark.fast
class TestShellEnvironment:
    """Tests for ShellEnvironment with real command execution."""

    @pytest.fixture
    def shell_env(self):
        """Create a shell environment with temp directory."""
        env = ShellEnvironment(
            task_description="Test shell commands",
            max_steps=10,
        )
        yield env
        env.close()

    @pytest.mark.asyncio
    async def test_create_directory(self, shell_env):
        """Test creating a directory actually creates it."""
        obs, reward, done, info = await shell_env.step(
            ShellAction.create_dir("test_dir")
        )

        # Verify directory exists
        assert (shell_env.working_dir / "test_dir").exists()
        assert (shell_env.working_dir / "test_dir").is_dir()

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, shell_env):
        """Test writing and reading files."""
        # Write file
        obs, _, _, _ = await shell_env.step(
            ShellAction.write_file("test.txt", "Hello, World!")
        )

        # Verify file exists with correct content
        file_path = shell_env.working_dir / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_execute_command(self, shell_env):
        """Test command execution captures real output."""
        obs, reward, done, info = await shell_env.step(
            ShellAction.execute("echo 'test output'")
        )

        assert obs.success
        assert "test output" in obs.stdout
        assert obs.exit_code == 0

    @pytest.mark.asyncio
    async def test_list_directory(self, shell_env):
        """Test directory listing returns actual files."""
        # Create some files
        await shell_env.step(ShellAction.write_file("file1.txt", "content1"))
        await shell_env.step(ShellAction.write_file("file2.txt", "content2"))

        obs, _, _, _ = await shell_env.step(ShellAction.list_dir())

        assert obs.success
        listing = obs.directory_listing
        assert listing is not None
        assert len(listing) == 2

        names = [item["name"] for item in listing]
        assert "file1.txt" in names
        assert "file2.txt" in names

    @pytest.mark.asyncio
    async def test_failed_command(self, shell_env):
        """Test failed commands are captured correctly."""
        obs, _, _, _ = await shell_env.step(
            ShellAction.execute("ls /nonexistent_directory_xyz")
        )

        assert not obs.success
        assert obs.exit_code != 0
        assert obs.stderr is not None

    @pytest.mark.asyncio
    async def test_security_prevents_escape(self, shell_env):
        """Test that paths outside working dir are rejected."""
        with pytest.raises(ValueError, match="outside working directory"):
            await shell_env.step(ShellAction.read_file("/etc/passwd"))

    @pytest.mark.asyncio
    async def test_trajectory_tracking(self, shell_env):
        """Test that execution is tracked."""
        await shell_env.step(ShellAction.create_dir("dir1"))
        await shell_env.step(ShellAction.write_file("file1.txt", "content"))
        await shell_env.step(ShellAction.execute("echo 'hello'"))

        assert len(shell_env.trajectory) == 3

        # Verify trajectory contains real data
        for step in shell_env.trajectory:
            assert step.action is not None
            assert step.observation is not None
            assert step.state is not None
            assert step.step_number >= 0


@pytest.mark.fast
class TestEvaluationHarness:
    """Tests for rigorous evaluation that checks actual outcomes."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return RealEnvironmentEvaluator()

    @pytest.mark.asyncio
    async def test_file_exists_criterion(self, evaluator):
        """Test file existence is verified."""
        env = ShellEnvironment("Test file exists")

        # Create file
        await env.step(ShellAction.write_file("test.txt", "content"))

        # Create task with criterion
        task = EvaluatedTask(
            task_id="test_file",
            description="Create a file",
            environment_type="shell",
            criteria=[FileExistsCriterion("test.txt")],
            expected_steps=5,
        )

        result = await evaluator.evaluate_task(task, env, env.trajectory)

        assert result.all_criteria_passed
        assert result.criteria[0].passed
        assert result.criteria[0].actual_value is True

        env.close()

    @pytest.mark.asyncio
    async def test_file_content_criterion(self, evaluator):
        """Test file content is verified."""
        env = ShellEnvironment("Test file content")

        # Create file with specific content
        await env.step(
            ShellAction.write_file("script.py", "import flask\napp = Flask(__name__)")
        )

        task = EvaluatedTask(
            task_id="test_content",
            description="Create Python script",
            environment_type="shell",
            criteria=[
                FileExistsCriterion("script.py"),
                FileContentCriterion("script.py", expected_pattern=r"import flask"),
                FileContentCriterion(
                    "script.py", expected_pattern=r"Flask\(__name__\)"
                ),
            ],
            expected_steps=5,
        )

        result = await evaluator.evaluate_task(task, env, env.trajectory)

        assert result.all_criteria_passed
        assert len(result.criteria) == 3
        assert all(c.passed for c in result.criteria)

        env.close()

    @pytest.mark.asyncio
    async def test_failed_task_evaluation(self, evaluator):
        """Test that missing files cause task to fail."""
        env = ShellEnvironment("Test missing file")

        # Don't create the expected file
        await env.step(ShellAction.create_dir("some_dir"))

        task = EvaluatedTask(
            task_id="test_missing",
            description="Should have created specific file",
            environment_type="shell",
            criteria=[FileExistsCriterion("expected_file.txt")],
            expected_steps=5,
        )

        result = await evaluator.evaluate_task(task, env, env.trajectory)

        assert not result.all_criteria_passed
        assert not result.criteria[0].passed
        assert result.reward < 0.5

        env.close()


@pytest.mark.fast
class TestTaskScenarios:
    """Tests for realistic long-horizon task scenarios."""

    def test_task_registry(self):
        """Test task registry has realistic tasks."""
        tasks = list_tasks()

        assert len(tasks) > 0

        # Check task properties
        for task in tasks:
            assert "task_id" in task
            assert "description" in task
            assert "category" in task
            assert "difficulty" in task
            assert "expected_steps" in task

    def test_flask_api_task(self):
        """Test Flask API task has appropriate criteria."""
        task = get_task("flask_api_with_db")
        assert task is not None

        assert task.environment_type == "shell"
        assert task.expected_steps >= 10
        assert len(task.criteria) >= 5

        # Should check for Flask-specific patterns
        criterion_names = [c.name for c in task.criteria]
        assert any("app.py" in name for name in criterion_names)

    def test_python_package_task(self):
        """Test Python package task."""
        task = get_task("python_package_setup")
        assert task is not None

        assert task.expected_steps >= 15

        # Should require multiple files
        criterion_names = [c.name for c in task.criteria]
        assert any("setup.py" in name for name in criterion_names)
        assert any("README.md" in name for name in criterion_names)


@pytest.mark.fast
class TestJourneyTracking:
    """Tests for journey tracking across environments."""

    @pytest.mark.asyncio
    async def test_multi_environment_journey(self):
        """Test tracking journeys across multiple environments."""
        tracker = RealEnvironmentJourneyTracker(enable_flume_sync=False)

        # Start journey
        journey = tracker.begin_journey("Multi-environment task")
        assert journey is not None
        assert journey.task_description == "Multi-environment task"

        # Simulate shell environment segment
        shell_env = ShellEnvironment("Shell task", max_steps=3)
        await shell_env.step(ShellAction.create_dir("project"))
        await shell_env.step(
            ShellAction.write_file("project/main.py", "print('hello')")
        )

        # Create segment manually for test
        segment = TrajectorySegment(
            segment_id="shell_seg_1",
            environment_type="ShellEnvironment",
            task_id="shell_task",
            start_time=0,
            end_time=1,
            steps=shell_env.trajectory,
        )

        tracker.record_segment(segment)

        # End journey
        final_journey = tracker.end_journey(success=True, final_reward=0.8)

        assert final_journey.success is True
        assert final_journey.final_reward == 0.8
        assert len(final_journey.segments) == 1
        assert final_journey.compute_phi_score() > 0

        shell_env.close()

    def test_journey_persistence(self):
        """Test journeys are saved to disk."""
        tracker = RealEnvironmentJourneyTracker(enable_flume_sync=False)

        journey = tracker.begin_journey("Test persistence")

        # Create minimal segment
        segment = TrajectorySegment(
            segment_id="test_seg",
            environment_type="TestEnvironment",
            task_id="test",
            start_time=0,
            end_time=1,
        )

        tracker.record_segment(segment)
        final_journey = tracker.end_journey(success=True, final_reward=1.0)

        # Check journey was saved
        recent = tracker.get_recent_journeys(n=1)
        assert len(recent) == 1
        assert recent[0].journey_id == final_journey.journey_id


@pytest.mark.fast
class TestMetricsCollection:
    """Tests for metrics and observability."""

    def test_metrics_tracking(self):
        """Test metrics are tracked for environment executions."""
        collector = RealEnvironmentMetricsCollector()

        metrics = collector.begin_tracking("shell", "test_task")

        # Simulate steps
        collector.record_step(metrics, latency_ms=100, success=True)
        collector.record_step(metrics, latency_ms=150, success=True)
        collector.record_step(metrics, latency_ms=200, success=False)

        collector.finalize(metrics, success=True, reward=0.7, phi_score=0.65)

        # Check metrics
        assert metrics.total_steps == 3
        assert metrics.successful_steps == 2
        assert metrics.failed_steps == 1
        assert metrics.final_reward == 0.7
        assert metrics.phi_score == 0.65

    def test_aggregate_stats(self):
        """Test aggregate statistics across multiple runs."""
        collector = RealEnvironmentMetricsCollector()

        # Simulate multiple task executions
        for i in range(5):
            metrics = collector.begin_tracking("shell", f"task_{i}")
            collector.record_step(
                metrics, latency_ms=100 + i * 10, success=(i % 2 == 0)
            )
            collector.finalize(
                metrics,
                success=(i % 2 == 0),
                reward=0.5 + i * 0.1,
                phi_score=0.6,
            )

        stats = collector.get_aggregate_stats()

        assert stats["total_tasks"] == 5
        assert "success_rate" in stats
        assert "avg_reward" in stats
        assert "avg_phi_score" in stats


@pytest.mark.integration
class TestIntegration:
    """Integration tests for complete task execution."""

    @pytest.mark.asyncio
    async def test_complete_flask_task(self):
        """Test complete Flask API task execution and evaluation."""
        # Get task
        task = get_task("flask_api_with_db")
        assert task is not None

        # Create environment
        env = ShellEnvironment(task.description, max_steps=task.max_steps)

        # Execute minimal Flask app creation steps
        await env.step(ShellAction.write_file("requirements.txt", "Flask==3.0.0\n"))

        await env.step(
            ShellAction.write_file(
                "app.py",
                """from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

@app.route('/users', methods=['GET'])
def get_users():
    return jsonify([])

@app.route('/users', methods=['POST'])
def create_user():
    return jsonify({'id': 1}), 201

if __name__ == '__main__':
    app.run(debug=True)
""",
            )
        )

        # Evaluate
        evaluator = RealEnvironmentEvaluator()
        result = await evaluator.evaluate_task(task, env, env.trajectory)

        # Task should pass with these minimal requirements
        assert result.all_criteria_passed
        assert result.reward > 0.5

        # Verify files exist
        assert (env.working_dir / "app.py").exists()
        assert (env.working_dir / "requirements.txt").exists()

        # Verify content
        app_content = (env.working_dir / "app.py").read_text()
        assert "from flask import Flask" in app_content
        assert "@app.route('/users'" in app_content

        env.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
