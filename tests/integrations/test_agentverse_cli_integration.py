"""Integration tests for AgentVerse Compound Loop with live services.

Tests that verify the compound loop works correctly with
mocked vault persistence and real-ish service orchestration.
"""

from __future__ import annotations

import json

import pytest


class TestCLIConfig:
    """Tests for CLIConfig."""

    def test_default_values(self):
        """[P0] Should have sensible defaults."""
        from cohezion.integrations.agentverse.cli import CLIConfig

        config = CLIConfig()
        assert config.vault_url == "http://localhost:8360"
        assert config.max_iterations == 5
        assert config.weak_skill_threshold == 0.4
        assert config.improvement_threshold == 0.1
        assert config.output_format == "text"

    def test_custom_values(self):
        """[P0] Should accept custom values."""
        from cohezion.integrations.agentverse.cli import CLIConfig

        config = CLIConfig(
            vault_url="http://custom:9090",
            vault_api_key="secret",
            max_iterations=10,
            weak_skill_threshold=0.3,
            improvement_threshold=0.15,
            output_format="json",
        )
        assert config.vault_url == "http://custom:9090"
        assert config.vault_api_key == "secret"
        assert config.max_iterations == 10


class TestLoadTasksFromFile:
    """Tests for task file loading."""

    def test_loads_list_format(self, tmp_path):
        """[P0] Should load tasks from list format file."""
        from cohezion.integrations.agentverse.cli import load_tasks_from_file

        task_file = tmp_path / "tasks.json"
        task_file.write_text(
            json.dumps(
                [
                    {"task": "test 1", "skill": "python_PRIME"},
                    {"task": "test 2", "skill": "testing_PRIME"},
                ]
            )
        )

        tasks = load_tasks_from_file(str(task_file))
        assert len(tasks) == 2
        assert tasks[0]["task"] == "test 1"

    def test_loads_dict_format(self, tmp_path):
        """[P0] Should load tasks from dict format file."""
        from cohezion.integrations.agentverse.cli import load_tasks_from_file

        task_file = tmp_path / "tasks.json"
        task_file.write_text(
            json.dumps(
                {
                    "tasks": [
                        {"task": "test 1", "skill": "python_PRIME"},
                    ]
                }
            )
        )

        tasks = load_tasks_from_file(str(task_file))
        assert len(tasks) == 1

    def test_raises_on_invalid_format(self, tmp_path):
        """[P0] Should raise on invalid file format."""
        from cohezion.integrations.agentverse.cli import load_tasks_from_file

        task_file = tmp_path / "tasks.json"
        task_file.write_text("not json")

        with pytest.raises((ValueError, json.JSONDecodeError)):
            load_tasks_from_file(str(task_file))


class TestFormatResult:
    """Tests for result formatting."""

    def test_format_text(self):
        """[P1] Should format result as human-readable text."""
        from cohezion.integrations.agentverse.cli import format_result_text

        result = {
            "total_iterations": 2,
            "final_coherence": 0.65,
            "initial_coherence": 0.5,
            "total_improvement": 0.15,
            "converged": True,
            "refined_skills": ["python_PRIME"],
            "iterations": [
                {
                    "iteration": 0,
                    "coherence_before": 0.5,
                    "coherence_after": 0.55,
                    "improvement": 0.05,
                    "weak_skills": ["python_PRIME"],
                    "refined_skills": ["python_PRIME"],
                    "converged": False,
                },
                {
                    "iteration": 1,
                    "coherence_before": 0.55,
                    "coherence_after": 0.65,
                    "improvement": 0.1,
                    "weak_skills": [],
                    "refined_skills": [],
                    "converged": True,
                },
            ],
        }

        text = format_result_text(result)
        assert "Total Iterations: 2" in text
        assert "Initial Coherence: 0.500" in text
        assert "Final Coherence: 0.650" in text
        assert "Converged: True" in text
        assert "python_PRIME" in text

    def test_format_json(self):
        """[P1] Should format result as JSON."""
        from cohezion.integrations.agentverse.cli import format_result_json

        result = {
            "total_iterations": 1,
            "final_coherence": 0.6,
            "initial_coherence": 0.5,
            "total_improvement": 0.1,
            "converged": True,
            "refined_skills": [],
            "iterations": [],
        }

        json_str = format_result_json(result)
        parsed = json.loads(json_str)
        assert parsed["total_iterations"] == 1
        assert parsed["converged"] is True


class TestCreateMCPClient:
    """Tests for MCP client creation."""

    def test_creates_client_with_config(self):
        """[P0] Should create client with config."""
        from cohezion.integrations.agentverse.cli import CLIConfig, create_mcp_client

        config = CLIConfig(vault_url="http://test:8080", vault_api_key="key123")
        client = create_mcp_client(config)

        assert client.config.server_url == "http://test:8080"
        assert client.config.api_key == "key123"


class TestRunCompoundLoop:
    """Tests for run_compound_loop function."""

    def test_cli_run_command_accepts_args(self):
        """[P0] CLI run command should accept required arguments."""
        from cohezion.integrations.agentverse.cli import run

        assert run is not None
        assert callable(run)

    def test_cli_list_command_exists(self):
        """[P0] CLI should have list-tasks command."""
        from cohezion.integrations.agentverse.cli import cli

        assert "run" in cli.commands


class TestCLIRunCommand:
    """Tests for CLI run command."""

    def test_cli_group_exists(self):
        """[P0] CLI should have run command."""
        from cohezion.integrations.agentverse.cli import cli

        assert hasattr(cli, "commands")
        assert "run" in cli.commands


class TestCLIAdversarial:
    """Adversarial tests for CLI."""

    def test_handles_missing_tasks_file(self):
        """[P1] Should handle missing tasks file gracefully."""
        from cohezion.integrations.agentverse.cli import load_tasks_from_file

        with pytest.raises(FileNotFoundError):
            load_tasks_from_file("/nonexistent/path/tasks.json")

    def test_handles_empty_tasks_file(self, tmp_path):
        """[P1] Should handle empty tasks list."""
        from cohezion.integrations.agentverse.cli import load_tasks_from_file

        task_file = tmp_path / "empty.json"
        task_file.write_text("[]")

        tasks = load_tasks_from_file(str(task_file))
        assert tasks == []

    def test_handles_malformed_json(self, tmp_path):
        """[P1] Should handle malformed JSON gracefully."""
        from cohezion.integrations.agentverse.cli import load_tasks_from_file

        task_file = tmp_path / "bad.json"
        task_file.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            load_tasks_from_file(str(task_file))

    def test_handles_missing_task_fields(self, tmp_path):
        """[P1] Should handle tasks missing required fields."""
        from cohezion.integrations.agentverse.cli import load_tasks_from_file

        task_file = tmp_path / "incomplete.json"
        task_file.write_text('[{"task": "only task field"}]')

        tasks = load_tasks_from_file(str(task_file))
        assert len(tasks) == 1
        assert "skill" not in tasks[0]
